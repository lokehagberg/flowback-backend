from typing import Union

from django.db.models import Q
from django.shortcuts import get_object_or_404
from backend.settings import env
from rest_framework.exceptions import ValidationError
from flowback.user.models import User
from flowback.group.models import Group, GroupUser, GroupUserInvite, GroupUserDelegator, GroupTags, GroupPermissions, \
    GroupUserDelegate
from flowback.group.selectors import group_user_permissions
from flowback.common.services import model_update, get_object


def group_create(*, user: int, name: str, description: str, image: str, cover_image: str,
                 public: bool, direct_join: bool) -> Group:

    user = get_object(User, id=user)

    if not (env('FLOWBACK_ALLOW_GROUP_CREATION') or (user.is_staff or user.is_superuser)):
        raise ValidationError('Permission denied')

    group = Group(created_by=user, name=name, description=description, image=image,
                  cover_image=cover_image, public=public, direct_join=direct_join)
    group.full_clean()
    group.save()
    GroupUser.objects.create(user=user, group=group, is_admin=True)

    return group


def group_update(*, user: int, group: int, data) -> Group:
    user = group_user_permissions(group=group, user=user, permissions=['admin'])
    non_side_effect_fields = ['name', 'description', 'image', 'cover_image', 'public',
                              'direct_join', 'default_permission']

    # Check if group_permission exists to allow for a new default_permission
    if default_permission := data.get('default_permission'):
        get_object(GroupPermissions, id=default_permission, author_id=group)

    group, has_updated = model_update(instance=user.group,
                                      fields=non_side_effect_fields,
                                      data=data)

    return group


def group_delete(*, user: int, group: int) -> None:
    group_user_permissions(group=group, user=user, permissions=['creator']).group.delete()


def group_permission_create(*,
                            user: int,
                            group: int,
                            role_name: str,
                            invite_user: bool,
                            create_poll: bool,
                            allow_vote: bool,
                            kick_members: bool,
                            ban_members: bool) -> None:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    group_permissions = GroupPermissions(role_name=role_name,
                                         author_id=group,
                                         invite_user=invite_user,
                                         create_poll=create_poll,
                                         allow_vote=allow_vote,
                                         kick_members=kick_members,
                                         ban_members=ban_members)
    group_permissions.full_clean()
    group_permissions.save()


def group_permission_update(*, user: int, group: int, permission_id: int, data) -> GroupPermissions:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    non_side_effect_fields = ['role_name', 'invite_user', 'create_poll', 'allow_vote', 'kick_members', 'ban_members']
    group_permission = get_object(GroupPermissions, id=permission_id, author_id=group)

    group_permission, has_updated = model_update(instance=group_permission,
                                                 fields=non_side_effect_fields,
                                                 data=data)

    return group_permission


def group_permission_delete(*, user: int, group: int, permission_id: int) -> None:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    get_object(GroupPermissions, id=permission_id).delete()


def group_join(*, user: int, group: int) -> Union[GroupUser, GroupUserInvite]:
    user = get_object(User, id=user)
    group = get_object(Group, id=group)

    if not group.public:
        raise ValidationError('Permission denied')

    get_object(GroupUser, 'User already joined', reverse=True, user=user, group=group)
    get_object(GroupUserInvite, 'User already requested invite', reverse=True, user=user, group=group)

    if not group.direct_join:
        user_status = GroupUserInvite(user=user, group=group)

    else:
        user_status = GroupUser(user=user, group=group)

    user_status.full_clean()
    user_status.save()

    return user_status


def group_user_update(*, user: int, group: int, fetched_by: int, data) -> GroupUser:
    user_to_update = group_user_permissions(group=group, user=fetched_by)
    non_side_effect_fields = []
    custom_fields = []

    # Custom delegate field
    if user_to_update.user.id == user and data.get('delegate'):
        get_object(GroupUserDelegate, 'User is already a delegate', reverse=True, user=user_to_update, group_id=group)
        delegate = GroupUserDelegate(user=user_to_update, group_id=group)
        delegate.full_clean()
        custom_fields.append(delegate)

    # If user updates someone else (requires Admin)
    if group_user_permissions(group=group, user=fetched_by, raise_exception=False, permissions=['admin']):
        user_to_update = group_user_permissions(group=group, user=user)
        non_side_effect_fields.extend(['permission', 'is_admin'])

    group_user, has_updated = model_update(instance=user_to_update,
                                           fields=non_side_effect_fields,
                                           data=data)

    for field in custom_fields:
        field.save()

    if custom_fields:
        group_user = get_object(GroupUser, user_id=user, group_id=group)

    return group_user


def group_leave(*, user: int, group: int) -> None:
    group_user_permissions(group=group, user=user).delete()


def group_invite(*, user: int, group: int, to: int) -> GroupUserInvite:
    group = group_user_permissions(group=group, user=user, permissions=['admin', 'invite_user']).group
    get_object(GroupUser, error_message='User is already in the group', reverse=True, group=group, user=to)
    invite = GroupUserInvite(user_id=to, group_id=group.id, external=False)
    invite.full_clean()
    invite.save()

    return invite


def group_invite_remove(*, user: int, group: int, to: int) -> None:
    group_user_permissions(group=group, user=user, permissions=['admin', 'invite_user'])
    invite = get_object(GroupUserInvite, 'User has not been invited', group_id=group, user_id=to)
    invite.delete()


def group_invite_accept(*, user: int, group: int) -> None:
    get_object(GroupUser, 'User already joined', reverse=True, user=user, group=group)
    invite = get_object(GroupUserInvite, 'User has not been invited', user_id=user, group_id=group)
    GroupUser.objects.create(user_id=user, group_id=group)
    invite.delete()


def group_invite_reject(*, user: int, group: int) -> None:
    get_object(GroupUser, 'User already joined', reverse=True, user_id=user, group_id=group)
    invite = get_object(GroupUserInvite, 'User has not been invited', user_id=user, group_id=group)
    invite.delete()


def group_tag_create(*, user: int, group: int, tag_name: str) -> GroupTags:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    tag = GroupTags(tag_name=tag_name, group_id=group)
    tag.full_clean()
    tag.save()

    return tag


def group_tag_update(*, user: int, group: int, tag: int, data) -> GroupTags:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    tag = get_object(GroupTags, group_id=group, id=tag)
    non_side_effect_fields = ['active']

    group_tag, has_updated = model_update(instance=tag,
                                          fields=non_side_effect_fields,
                                          data=data)

    return group_tag


def group_tag_delete(*, user: int, group: int, tag: int) -> None:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    tag = get_object(GroupTags, group_id=group, id=tag)
    tag.delete()


def group_user_delegate(*, user: int, group: int, delegate: int, tags: list[int] = None) -> GroupUserDelegator:
    tags = tags or []
    delegator = group_user_permissions(group=group, user=user)
    delegate = get_object(GroupUserDelegate, 'Delegate does not exist', id=delegate, group=group)

    db_tags = GroupTags.objects.filter(id__in=tags, active=True).all()

    # Check if user_tags already exists
    user_tags = GroupTags.objects.filter(Q(groupuserdelegator__delegator=delegator,
                                           groupuserdelegator__group_id=group) &
                                         Q(id__in=tags))
    if user_tags.exists():
        raise ValidationError(f'User has already subscribed to '
                              f'{", ".join([x.tag_name for x in user_tags.all()])}')

    # Check if tags exist in group
    if len(db_tags) < len(tags):
        raise ValidationError('Not all tags are available in the group')

    delegate_rel = GroupUserDelegator(group_id=group, delegator_id=delegator.id,
                                      delegate_id=delegate.id)
    delegate_rel.full_clean()
    delegate_rel.save()
    delegate_rel.tags.add(*db_tags)

    return delegate_rel


def group_user_delegate_remove(*, user_id: int, group_id: int, delegate_id: int) -> None:
    delegator = group_user_permissions(group=group_id, user=user_id)
    delegate = get_object(GroupUserDelegate, 'Delegate does not exist', id=delegate_id)

    delegate_rel = get_object(GroupUserDelegator, 'User to delegate relation does not exist',
                              delegator=delegator, group_id=group_id, delegate=delegate)

    delegate_rel.delete()


def group_user_delegate_update(*, user_id: int, group_id: int, delegate_id: int, tags: list[int] = None) -> GroupUserDelegator:
    group_user_delegate_remove(user_id=user_id, group_id=group_id, delegate_id=delegate_id)
    new_delegate_rel = group_user_delegate(user=user_id, group=group_id, delegate=delegate_id, tags=tags)

    return new_delegate_rel
