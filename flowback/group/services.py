from django.db.models import Q
from django.shortcuts import get_object_or_404
from backend.settings import env
from rest_framework.exceptions import ValidationError
from flowback.user.models import User
from flowback.group.models import Group, GroupUser, GroupUserInvite, GroupUserDelegate, GroupTags
from flowback.group.selectors import group_user_permissions
from flowback.common.services import model_update, get_object
# TODO Leave, Invite_Request, Invite, Invite_Reject, Invite_Verify, Delegate, Remove_Delegate


def group_create(*, user: int, name: str, description: str, image: str, cover_image: str,
                 public: bool, direct_join: bool) -> Group:
    user = get_object(User, id=user)

    if not (env('ALLOW_GROUP_CREATION') or (user.is_staff or user.is_superuser)):
        raise ValidationError('Permission denied')

    group = Group.objects.create(created_by=user, name=name, description=description, image=image,
                                 cover_image=cover_image, public=public, direct_join=direct_join)

    return group


def group_update(*, user: int, group: int, data) -> Group:
    user = group_user_permissions(group=group, user=user, permissions=['admin'])
    non_side_effect_fields = ['name', 'description', 'image', 'cover_image', 'public', 'direct_join']

    group, has_updated = model_update(instance=user.group,
                                      fields=non_side_effect_fields,
                                      data=data)

    return group


def group_delete(*, user: int, group: int) -> None:
    group_user_permissions(group=group, user=user, permissions=['creator']).group.delete()


def group_join(*, user: int, group: int) -> None:
    user = get_object(User, id=user)
    group = get_object_or_404(Group, id=group)

    if not group.public:
        raise ValidationError('Permission denied')

    get_object(GroupUser, 'User already joined', reverse=True, user=user, group=group)
    get_object(GroupUserInvite, 'User already requested invite', user=user, group=group)

    if not group.direct_join:
        GroupUserInvite.objects.create(user=user, group=group)

    else:
        GroupUser.objects.create(user=user, group=group)


def group_leave(*, user: int, group: int) -> None:
    group_user_permissions(group=group, user=user).delete()


def group_invite(*, user: int, group: int, to: int):
    group = group_user_permissions(group=group, user=user, permissions=['admin', 'invite_user']).group
    GroupUserInvite.objects.create(user=to, group=group)


def group_invite_remove(*, user: int, group: int, to: int):
    group_user_permissions(group=group, user=user, permissions=['admin', 'invite_user'])
    invite = get_object(GroupUserInvite, 'User has not been invited', reverse=True, group_id=group, user_id=to)
    invite.delete()


def group_invite_accept(*, user: int, group: int):
    get_object(GroupUser, 'User already joined', reverse=True, user=user, group=group)
    invite = get_object(GroupUserInvite, 'User has not been invited', user_id=user, group_id=group)
    GroupUser.objects.create(user_id=user, group_id=group)
    invite.delete()


def group_invite_reject(*, user: int, group: int):
    get_object(GroupUser, 'User already joined', reverse=True, user_id=user, group_id=group)
    invite = get_object(GroupUserInvite, 'User has not been invited', user_id=user, group_id=group)
    invite.delete()


def group_user_delegate(*, user: int, group: int, delegate: int, tags: list = None):
    tags = tags or []
    delegator = group_user_permissions(group=group, user=user)
    delegate = get_object(GroupUser, 'Delegate does not exist', user_id=delegate, group_id=group, is_delegate=True)

    db_tags = GroupTags.objects.filter(tag_name__in=tags, active=False).all()

    # Check if user_tags already exists
    user_tags = GroupTags.objects.filter(Q(groupuserdelegate__delegate=delegate,
                                           groupuserdelegate__delegator=delegator,
                                           groupuserdelegate__group_id=group) &
                                         Q(tag_name__in=tags))
    if user_tags.exists():
        raise ValidationError(f'User has already subscribed to '
                              f'{", ".join([x.tag_name for x in user_tags.all()])}')

    # Check if tags exist in group
    if len(db_tags) < len(tags):
        raise ValidationError('Not all tags exists in the group')

    delegate_rel = GroupUserDelegate.objects.create(group_id=group, delegator_id=user, delegate_id=delegate)
    delegate_rel.tags.add(*db_tags)


def group_user_delegate_remove(*, user: int, group: int, delegate: int):
    delegator = group_user_permissions(group=group, user=user)
    delegate = get_object(GroupUser, 'Delegate does not exist', user_id=delegate, group_id=group, is_delegate=True)
    delegate_rel = get_object(GroupUserDelegate, 'User to delegate relation does not exist',
                              delegator=delegator, group_id=group, delegate=delegate)

    delegate_rel.delete()


def group_user_delegate_update(*, user: int, group: int, delegate: int, tags: list = None):
    group_user_delegate_remove(user=user, group=group, delegate=delegate)
    group_user_delegate(user=user, group=group, delegate=delegate, tags=tags)
