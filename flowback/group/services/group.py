from typing import Union

from django.core.mail import send_mass_mail
from rest_framework.exceptions import ValidationError

from backend.settings import env, DEFAULT_FROM_EMAIL
from flowback.common.services import get_object, model_update
from flowback.group.models import Group, GroupUser, GroupPermissions, GroupUserInvite
from flowback.group.selectors import group_user_permissions
from flowback.notification.services import NotificationManager
from flowback.user.models import User

group_notification = NotificationManager(sender_type='group', possible_categories=['group', 'members', 'invite',
                                                                                   'delegate', 'poll', 'kanban',
                                                                                   'schedule', 'poll_schedule'])


def group_create(*,
                 user: int,
                 name: str,
                 description: str,
                 hide_poll_users: bool,
                 public: bool,
                 direct_join: bool,
                 image: str = None,
                 cover_image: str = None,
                 blockchain_id: int = None) -> Group:
    user = get_object(User, id=user)

    if not (env('FLOWBACK_ALLOW_GROUP_CREATION') or (user.is_staff or user.is_superuser)):
        raise ValidationError('Permission denied')

    # Create Group
    group = Group(created_by=user, name=name, description=description, image=image,
                  cover_image=cover_image, hide_poll_users=hide_poll_users, public=public, direct_join=direct_join,
                  blockchain_id=blockchain_id)
    # TODO Fullclean MUST work!
    # group.full_clean()
    group.save()

    # Generate GroupUser
    GroupUser.objects.create(user=user, group=group, is_admin=True)

    return group


def group_update(*, user: int, group: int, data) -> Group:
    group_user = group_user_permissions(user=user, group=group, permissions=['admin'])
    non_side_effect_fields = ['name', 'description', 'image', 'cover_image', 'hide_poll_users',
                              'public', 'direct_join', 'default_permission', 'default_quorum']

    # Check if group_permission exists to allow for a new default_permission
    if default_permission := data.get('default_permission'):
        data['default_permission'] = get_object(GroupPermissions, id=default_permission, author_id=group)

    group, has_updated = model_update(instance=group_user.group,
                                      fields=non_side_effect_fields,
                                      data=data)

    group_notification.create(sender_id=group.id, action=group_notification.Action.update, category='group',
                              message=f'{group_user.user.username} updated the group information in {group.name}')

    return group


def group_delete(*, user: int, group: int) -> None:
    group_user_permissions(user=user, group=group, permissions=['creator']).group.delete()


def group_mail(*, fetched_by: int, group: int, title: str, message: str) -> None:
    group_user = group_user_permissions(user=fetched_by, group=group, permissions=['admin'])

    subject = f'[{group_user.group.name}] - {title}'
    targets = GroupUser.objects.filter(group_id=group).values('user__email').all()

    send_mass_mail([subject, message, DEFAULT_FROM_EMAIL,
                    [target['user__email']]] for target in targets)


def group_join(*, user: int, group: int) -> Union[GroupUser, GroupUserInvite]:
    user = get_object(User, id=user)
    group = get_object(Group, id=group)

    if not group.public:
        raise ValidationError('Permission denied')

    get_object(GroupUser, 'User already joined', reverse=True, user=user, group=group)
    get_object(GroupUserInvite, 'User already requested invite', reverse=True, user=user, group=group)

    if not group.direct_join:
        user_status = GroupUserInvite(user=user, group=group, external=True)
        group_notification.create(sender_id=group.id, action=group_notification.Action.update,
                                  category='invite', message=f'User {user.username} requested to join {group.name}')

        user_status.full_clean()
        user_status.save()

    else:
        try:
            user_status = GroupUser.objects.get(user=user, group=group)
            user_status.active = True
            user_status.save()
        except GroupUser.DoesNotExist:
            user_status = GroupUser(user=user, group=group)
            # user_status.full_clean() TODO fix
            user_status.save()

    group_notification.create(sender_id=group.id, action=group_notification.Action.create,
                              category='members', message=f'User {user.username} joined the group {group.name}')

    return user_status


def group_leave(*, user: int, group: int) -> None:
    user = group_user_permissions(user=user, group=group)

    if user.user == user.group.created_by:
        raise ValidationError("Group owner isn't allowed to leave, deleting the group is an option")

    user.active = False
    user.save()

    group_notification.create(sender_id=group, action=group_notification.Action.create,
                              category='members', message=f'User {user.user.username} left the group {user.group.name}')


def group_user_update(*, user: int, group: int, fetched_by: int, data) -> GroupUser:
    user_to_update = group_user_permissions(user=fetched_by, group=group)
    non_side_effect_fields = []

    # If user updates someone else (requires Admin)
    if group_user_permissions(user=fetched_by, group=group, permissions=['admin'], raise_exception=False):
        user_to_update = group_user_permissions(user=user, group=group)
        non_side_effect_fields.extend(['permission_id', 'is_admin'])

    group_user, has_updated = model_update(instance=user_to_update,
                                           fields=non_side_effect_fields,
                                           data=data)

    return group_user


def group_notification_subscribe(*, user_id: int, group: int, categories: list[str]):
    group_user = group_user_permissions(user=user_id, group=group)

    if 'invite' in categories and (not group_user.is_admin or not group_user.check_permission(invite_user=True)):
        raise ValidationError('Permission denied for invite notifications')

    group_notification.channel_subscribe(user_id=user_id, sender_id=group, category=categories)
