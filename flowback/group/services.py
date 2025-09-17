from django.shortcuts import get_object_or_404
from backend.settings import env
from rest_framework.exceptions import ValidationError
from flowback.user.models import User
from flowback.group.models import Group, GroupUser, GroupUserInvite
from flowback.common.services import model_update
# TODO Create, Update, Delete, Join, Leave, Invite, Invite_Verify, Delegate, Remove_Delegate


def group_create(*, user: int, name: str, description: str, image: str, cover_image: str,
                 public: bool, direct_join: bool) -> Group:
    user = get_object_or_404(User, id=user)

    if not (env('ALLOW_GROUP_CREATION') or user.is_staff):
        raise ValidationError('Permission denied')

    group = Group.objects.create(created_by=user, name=name, description=description, image=image,
                                 cover_image=cover_image, public=public, direct_join=direct_join)

    return group


def group_update(*, user: int, group: int, data) -> Group:
    user = get_object_or_404(GroupUser, user=user, group=group)
    group = get_object_or_404(Group, id=group)
    non_side_effect_fields = ['name', 'description', 'image', 'cover_image', 'public', 'direct_join']

    if not user.is_admin:
        raise ValidationError('Permission denied')

    group, has_updated = model_update(instance=group,
                                      fields=non_side_effect_fields,
                                      data=data)

    return group


def group_delete(*, user: int, group: int) -> None:
    user = get_object_or_404(User, id=user)
    group = get_object_or_404(Group, id=group)

    if not (group.created_by == user or user.is_staff):
        raise ValidationError('Permission denied')

    if user == group.created_by:
        group.delete()

    return


def group_join(*, user: int, group: int) -> None:
    user = get_object_or_404(User, id=user)
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
