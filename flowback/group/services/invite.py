from flowback.common.services import get_object
from flowback.group.models import GroupUserInvite, GroupUser
from flowback.group.selectors.permission import group_user_permissions


def group_invite(*, user: int, group: int, to: int) -> GroupUserInvite:
    group = group_user_permissions(user=user, group=group, permissions=['admin', 'invite_user']).group
    get_object(GroupUser, error_message='User is already in the group', reverse=True, group=group, user=to, active=True)
    invite = GroupUserInvite(user_id=to, group_id=group.id, external=False)

    invite.full_clean()
    invite.save()

    return invite


def group_invite_remove(*, user: int, group: int, to: int) -> None:
    group_user_permissions(user=user, group=group, permissions=['admin', 'invite_user'])
    invite = get_object(GroupUserInvite, 'User has not been invited', group_id=group, user_id=to)
    invite.delete()


def group_invite_accept(*, fetched_by: int, group: int, to: int = None) -> None:
    if to:
        group_user_permissions(user=fetched_by, group=group, permissions=['invite_user', 'admin'])
        get_object(GroupUser, 'User already joined', reverse=True, user_id=to, group=group, active=True)
        invite = get_object(GroupUserInvite, 'User has not requested invite', user_id=to, group_id=group, external=True)

        # Check if user is already a group user
        if group_user := get_object(GroupUser, raise_exception=False, user_id=to, group_id=group, active=False):
            group_user.active = True
        else:
            group_user = GroupUser(user_id=to, group_id=group)

    else:
        invite = get_object(GroupUserInvite, 'User has not been invited', user_id=fetched_by, group_id=group,
                            external=False)

        # Check if user is already a group user
        if group_user := get_object(GroupUser, raise_exception=False, user_id=fetched_by, group_id=group, active=False):
            group_user.active = True
        else:
            group_user = GroupUser(user_id=fetched_by, group_id=group)

    # TODO fix group_user.full_clean()
    group_user.save()
    invite.delete()


def group_invite_reject(*, fetched_by: id, group: int, to: int = None) -> None:
    if to:
        get_object(GroupUser, 'User already joined',
                   reverse=True,
                   user_id=to,
                   group_id=group,
                   active=True)
        group_user_permissions(user=fetched_by, group=group, permissions=['invite_user', 'admin'])
        invite = get_object(GroupUserInvite, 'User has not been invited', user_id=to, group_id=group)

    else:
        get_object(GroupUser,
                   'User already joined',
                   reverse=True,
                   user_id=fetched_by,
                   group_id=group,
                   active=True)
        invite = get_object(GroupUserInvite, 'User has not requested invite', user_id=fetched_by, group_id=group)

    invite.delete()
