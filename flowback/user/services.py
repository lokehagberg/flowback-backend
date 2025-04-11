import logging
import operator
import uuid
from functools import reduce

from django.core.mail import send_mail
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from backend.settings import DEFAULT_FROM_EMAIL, FLOWBACK_URL, EMAIL_HOST
from flowback.chat.models import MessageChannel, MessageChannelParticipant
from flowback.chat.services import message_channel_create, message_channel_join
from flowback.common.services import model_update, get_object
from flowback.kanban.services import KanbanManager
from flowback.schedule.models import ScheduleEvent
from flowback.schedule.services import ScheduleManager, unsubscribe_schedule
from flowback.user.models import User, OnboardUser, PasswordReset, Report, UserChatInvite

user_schedule = ScheduleManager(schedule_origin_name='user')
user_kanban = KanbanManager(origin_type='user')


def user_create(*, username: str, email: str) -> OnboardUser | None:
    users = User.objects.filter(Q(email=email) | Q(username=username))
    if users.exists():
        for user in users:
            if user.email == email:
                raise ValidationError('Email already exists.')

            else:
                raise ValidationError('Username already exists.')

    user = OnboardUser.objects.create(email=email, username=username)

    link = f'Use this code to create your account: {user.verification_code}'
    if FLOWBACK_URL:
        link = f'''Use this link to create your account: {FLOWBACK_URL}/create_account/
                   ?email={email}&verification_code={user.verification_code}'''

    if EMAIL_HOST:
        send_mail('Flowback Verification Code', link, DEFAULT_FROM_EMAIL, [email])

    else:
        logging.info("Email host not configured. Email not sent, but code was sent to the console.")
        print(f"Verification code for '{user.username}': {user.verification_code}")

        return user


def user_create_verify(*, verification_code: str, password: str):
    onboard_user = get_object_or_404(OnboardUser, verification_code=verification_code)

    if User.objects.filter(email=onboard_user.email).exists():
        raise ValidationError('Email already registered')

    elif User.objects.filter(username=onboard_user.username).exists():
        raise ValidationError('Username already registered')

    elif onboard_user.is_verified:
        raise ValidationError('Verification code has already been used.')

    validate_password(password)

    model_update(instance=onboard_user,
                 fields=['is_verified'],
                 data=dict(is_verified=True))

    return User.objects.create_user(username=onboard_user.username,
                                    email=onboard_user.email,
                                    password=password)


def user_forgot_password(*, email: str) -> PasswordReset:
    user = get_object_or_404(User, email=email)

    password_reset = PasswordReset.objects.create(user=user)

    link = f'Use this code to reset your account password: {password_reset.verification_code}'

    if FLOWBACK_URL:
        link = f'''Use this link to reset your account password: {FLOWBACK_URL}/forgot_password/
                       ?email={email}&verification_code={password_reset.verification_code}'''

    if EMAIL_HOST:
        send_mail('Flowback Verification Code', link, DEFAULT_FROM_EMAIL, [email])

    else:
        logging.info("Email host not configured. Email not sent, but code was sent to the console.")
        print(f"Verification code for '{user.username}': {password_reset.verification_code}")

    return password_reset


def user_forgot_password_verify(*, verification_code: str, password: str):
    password_reset = get_object_or_404(PasswordReset, verification_code=verification_code)

    if password_reset.is_verified:
        raise ValidationError('Verification code has already been used.')

    validate_password(password)
    user = password_reset.user
    user.set_password(password)
    user.save()

    model_update(instance=password_reset,
                 fields=['is_verified'],
                 data=dict(is_verified=True))

    return user


def user_update(*, user: User, data) -> User:
    non_side_effects_fields = ['username', 'email',
                               'profile_image', 'banner_image', 'bio',
                               'website', 'email_notifications',
                               'dark_theme', 'contact_email',
                               'contact_phone',
                               'user_config', 'public_status', 'chat_status']

    user, has_updated = model_update(instance=user,
                                     fields=non_side_effects_fields,
                                     data=data)

    return user


def user_delete(*, user_id: int) -> None:
    user = get_object(User, id=user_id)

    if user.is_active:
        user.is_active = False
        user.username = 'deleted_user_' + uuid.uuid4().hex
        user.email = user.username + '@example.com'
        user.profile_image = None
        user.banner_image = None
        user.email_notifications = False
        user.bio = None
        user.website = None

        user.full_clean()
        user.save()

        user.schedule.delete()
        user.kanban.delete()


def user_schedule_event_create(*,
                               user_id: int,
                               title: str,
                               start_date: timezone.datetime,
                               description: str = None,
                               end_date: timezone.datetime = None) -> ScheduleEvent:
    user = get_object(User, id=user_id)
    return user_schedule.create_event(schedule_id=user.schedule.id,
                                      title=title,
                                      start_date=start_date,
                                      end_date=end_date,
                                      origin_id=user.id,
                                      origin_name='user',
                                      description=description)


def user_schedule_event_update(*, user_id: int, event_id: int, **data):
    user = get_object(User, id=user_id)
    user_schedule.update_event(event_id=event_id, schedule_origin_id=user.id, data=data)


def user_schedule_event_delete(*, user_id: int, event_id: int):
    user = get_object(User, id=user_id)
    user_schedule.delete_event(event_id=event_id, schedule_origin_id=user.id)


def user_schedule_unsubscribe(*,
                              user_id: int,
                              target_type: str,
                              target_id: int):
    user = get_object(User, id=user_id)
    schedule = user_schedule.get_schedule(origin_id=user_id)
    target_schedule = user_schedule.get_schedule(origin_name=target_type, origin_id=target_id)
    unsubscribe_schedule(schedule_id=schedule.id, target_id=target_schedule.id)


def user_kanban_entry_create(*,
                             user_id: int,
                             assignee_id: int = None,
                             title: str,
                             description: str = None,
                             attachments: list = None,
                             priority: int,
                             lane: int,
                             end_date: timezone.datetime = None):
    return user_kanban.kanban_entry_create(origin_id=user_id,
                                           created_by_id=user_id,
                                           assignee_id=assignee_id,
                                           title=title,
                                           description=description,
                                           attachments=attachments,
                                           priority=priority,
                                           end_date=end_date,
                                           lane=lane)


def user_kanban_entry_update(*, user_id: int, entry_id: int, data):
    return user_kanban.kanban_entry_update(origin_id=user_id,
                                           entry_id=entry_id,
                                           data=data)


def user_kanban_entry_delete(*, user_id: int, entry_id: int):
    return user_kanban.kanban_entry_delete(origin_id=user_id,
                                           entry_id=entry_id)


def user_get_chat_channel(fetched_by: User, target_user_ids: int | list[int], preview: bool = False) -> MessageChannel:
    if isinstance(target_user_ids, int):
        target_user_ids = [target_user_ids]

    if fetched_by.id not in target_user_ids:
        target_user_ids.append(fetched_by.id)

    target_users = User.objects.filter(id__in=target_user_ids, is_active=True)

    if not len(target_users) == len(target_user_ids):
        raise ValidationError("Not every user requested do exist")

    if len(target_user_ids) == 1 and fetched_by.id == target_user_ids[0]:
        raise ValidationError("Cannot create a chat with yourself")

    try:
        # Find a channel where all users are in the same chat
        channel = MessageChannel.objects.annotate(count=Count('users')).filter(
            count=target_users.count())

        for u in target_users.all():
            channel = channel.filter(users=u.id)

        channel = channel.first()

        if not channel:
            raise MessageChannel.DoesNotExist

        for u in target_users.all():
            UserChatInvite.objects.filter(user=u, message_channel=channel, rejected=True).update(rejected=None)

    except MessageChannel.DoesNotExist:
        if preview:
            raise ValidationError("MessageChannel does not exist between the participants")

        title = f"{', '.join([u.username for u in target_users])}"
        channel = message_channel_create(origin_name=f"{User.message_channel_origin}"
                                                     f"{'_group' if len(target_users) > 2 else ''}",
                                         title=title if len(target_users) > 1 else None)

        # In the future, make this a bulk_create statement
        share_groups = False

        if len(target_users) <= 2:
            share_groups = User.objects.filter(group__groupuser__user__in=target_users).exists()

        for u in target_users:
            u_is_public = u.chat_status == User.PublicStatus.PUBLIC
            u_is_group_only = u.chat_status == User.PublicStatus.GROUP_ONLY

            if (((u_is_public or (u_is_group_only and share_groups)) and len(target_users) <= 2)
                    or u.id == fetched_by.id
                    or fetched_by.is_superuser == True):
                message_channel_join(user_id=u.id, channel_id=channel.id)

            else:
                if not channel.messagechannelparticipant_set.filter(user_id=u.id).exists():
                    UserChatInvite.objects.update_or_create(user_id=u.id,
                                                            message_channel_id=channel.id,
                                                            rejected=False,
                                                            defaults=dict(rejected=None))

    return channel


def user_chat_channel_leave(*, user_id: int, channel_id: int):
    participant = MessageChannelParticipant.objects.get(channel_id=channel_id, user_id=user_id)

    if not participant.channel.origin_name == f'{User.message_channel_origin}_group':
        raise ValidationError("You can only leave user_group channels")

    participant.channel.delete()


def user_chat_invite(user_id: int, invite_id: int, accept: bool = True):
    user = User.objects.get(id=user_id)
    invite = UserChatInvite.objects.get(id=invite_id, rejected=None)

    if not invite.user == user:
        raise ValidationError("You cannot accept an invite for someone else")

    invite.rejected = not accept
    invite.save()


def user_chat_channel_update(*, user_id: int, channel_id: int, data: dict):
    if MessageChannelParticipant.objects.filter(channel_id=channel_id,
                                                user_id=user_id,
                                                active=True,
                                                channel__origin_name__in=[User.message_channel_origin,
                                                                          f'{User.message_channel_origin}_group']
                                                ).exists():
        channel, has_updated = model_update(instance=MessageChannel.objects.get(id=channel_id),
                                            fields=['title'],
                                            data=data)

        return channel


def report_create(*, user_id: int, title: str, description: str):
    user = get_object(User, id=user_id)

    report = Report(user=user, title=title, description=description)
    report.full_clean()
    report.save()

    return report
