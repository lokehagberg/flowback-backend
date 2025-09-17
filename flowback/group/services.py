from django.shortcuts import get_object_or_404
from backend.settings import env
from rest_framework.exceptions import ValidationError
from flowback.user.models import User
from flowback.user.selectors import get_user
from flowback.group.models import Group, GroupUser, GroupUserInvite
from flowback.group.selectors import group_user_permissions
from flowback.common.services import model_update, get_object
# TODO Leave, Invite_Request, Invite, Invite_Reject, Invite_Verify, Delegate, Remove_Delegate


def group_create(*, user: int, name: str, description: str, image: str, cover_image: str,
                 public: bool, direct_join: bool) -> Group:
    user = get_user(user=user)

    if not (env('ALLOW_GROUP_CREATION') or user.is_staff):
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
    user = get_user(user)
    group = get_object_or_404(Group, id=group)

    if not group.public:
        raise ValidationError('Permission denied')

    if GroupUser.objects.filter(user=user, group=group).exists():
        raise ValidationError('User already joined')

    if GroupUserInvite.objects.filter(user=user, group=group).exists():
        raise ValidationError('User already requested invite')

    if not group.direct_join:
        GroupUserInvite.objects.create(user=user, group=group)

    else:
        GroupUser.objects.create(user=user, group=group)


def group_leave(*, user: int, group: int) -> None:
    group_user_permissions(group=group, user=user).delete()
