from typing import Union

from django.core.mail import send_mass_mail
from rest_framework.exceptions import ValidationError

from backend.settings import env, DEFAULT_FROM_EMAIL, FLOWBACK_ALLOW_GROUP_CREATION, FLOWBACK_DEFAULT_GROUP_JOIN
from flowback.common.services import get_object, model_update
from flowback.group.models import Group, GroupUser, GroupPermissions, GroupUserInvite, WorkGroupUser
from flowback.group.selectors.permission import group_user_permissions
from flowback.user.models import User


def group_create(*,
                 user: int,
                 name: str,
                 description: str = None,
                 hide_poll_users: bool,
                 public: bool,
                 direct_join: bool,
                 image: str = None,
                 cover_image: str = None,
                 blockchain_id: int = None) -> Group:
    user = get_object(User, id=user)

    if not (env('FLOWBACK_ALLOW_GROUP_CREATION') or (user.is_staff or user.is_superuser)):
        raise ValidationError('Permission denied')

    # TODO Fullclean MUST work!
    if direct_join and not public:
        raise ValidationError('Private groups are unable to allow Direct Join')

    # Create Group
    group = Group(created_by=user, name=name, description=description, image=image,
                  cover_image=cover_image, hide_poll_users=hide_poll_users, public=public, direct_join=direct_join,
                  blockchain_id=blockchain_id)
    # TODO Fullclean MUST work!
    # group.full_clean()
    group.save()

    return group


def group_update(*, user: int, group_id: int, data) -> Group:
    group_user = group_user_permissions(user=user, group=group_id, permissions=['admin'])
    non_side_effect_fields = ['name', 'description', 'image', 'cover_image', 'hide_poll_users',
                              'public', 'direct_join', 'default_permission', 'default_quorum',
                              'poll_phase_minimum_space']

    # Check if group_permission exists to allow for a new default_permission
    if default_permission := data.get('default_permission'):
        data['default_permission'] = GroupPermissions.objects.get(id=default_permission, author_id=group_id)

    group, has_updated = model_update(instance=group_user.group,
                                         fields=non_side_effect_fields,
                                         data=data)

    group.notify_group(message=f"Group has been updated",
                          action=group.notification_channel.Action.UPDATED)

    return group


def group_delete(*, user: int, group: int) -> None:
    group_user_permissions(user=user, group=group, permissions=['creator']).group.delete()


def group_mail(*, fetched_by: int,
               group: int,
               title: str,
               message: str,
               target_user_ids: list[int] = None,
               work_group_id: int = None) -> None:
    group_user = group_user_permissions(user=fetched_by,
                                        group=group,
                                        permissions=['admin', 'send_group_email'],
                                        work_group=work_group_id)

    subject = f'[{group_user.group.name}] - {title}'
    target_user_ids = target_user_ids or []

    if not work_group_id:
        group_user_permissions(user=fetched_by,
                               group=group,
                               permissions=['admin', 'send_group_email'])

        targets = GroupUser.objects.filter(group_id=group,
                                           user_id__in=target_user_ids).values('user__email').all()

        send_mass_mail([subject, message, DEFAULT_FROM_EMAIL,
                        [target['user__email']]] for target in targets)

    else:
        group_user_permissions(user=fetched_by,
                               group=group,
                               permissions=['work_group_moderator'],
                               work_group=work_group_id,
                               allow_admin=True)

        targets = WorkGroupUser.objects.filter(work_group_id=work_group_id,
                                               group_user__user_id__in=target_user_ids
                                               ).values('group_user__user__email').all()

        send_mass_mail([subject, message, DEFAULT_FROM_EMAIL,
                        [target['group_user__user__email']]] for target in targets)


def group_join(*, user: int, group: int) -> Union[GroupUser, GroupUserInvite]:
    user = get_object(User, id=user)
    group = get_object(Group, id=group)

    if not group.public:
        raise ValidationError('Permission denied')

    get_object(GroupUser, 'User already joined', reverse=True, user=user, group=group, active=True)
    get_object(GroupUserInvite, 'User already requested invite', reverse=True, user=user, group=group)

    if not group.direct_join:
        user_status = GroupUserInvite(user=user, group=group, external=True)

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

    return user_status


def group_leave(*, user: int, group: int) -> None:
    user = group_user_permissions(user=user, group=group)

    if user.user == user.group.created_by:
        raise ValidationError("Group owner isn't allowed to leave, deleting the group is an option")

    user.active = False
    user.save()

def group_user_update(*, fetched_by: User, group: int, target_user_id: int, data) -> GroupUser:
    # If user updates someone else (requires Admin)
    group_user_permissions(user=fetched_by, group=group, permissions=['admin'])

    non_side_effect_fields = ['permission_id', 'is_admin']
    user_to_update = group_user_permissions(user=target_user_id, group=group)

    group_user, has_updated = model_update(instance=user_to_update,
                                           fields=non_side_effect_fields,
                                           data=data)

    if fetched_by.id != target_user_id:
        group_user.group.notify_group_user(_user_id=target_user_id,
                                           message=f"An Admin has changed your permissions",
                                           action=group_user.group.notification_channel.Action.CREATED)

    return group_user


def group_user_delete(*, user_id: int, group_id: int, target_user_id: int) -> None:
    if not FLOWBACK_ALLOW_GROUP_CREATION and group_id in FLOWBACK_DEFAULT_GROUP_JOIN:
        raise ValidationError("Can't delete a group user when group creation is disabled and group user is in "
                              "default group join list")

    group_user_permissions(user=user_id, group=group_id, permissions=['admin'])
    group_user_to_delete = group_user_permissions(user=target_user_id, group=group_id)

    if group_user_to_delete.is_admin:
        raise ValidationError("Can't delete a group user with admin status")

    group_user_to_delete.delete()


def group_notification_subscribe(*, user: User, group_id: int, **kwargs) -> None:
    group_user = group_user_permissions(user=user, group=group_id)
    group_user.group.notification_channel.subscribe(user=user, **kwargs)
