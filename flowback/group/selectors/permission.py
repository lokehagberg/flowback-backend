from typing import Union

import django_filters
from django.forms import model_to_dict
from rest_framework.exceptions import ValidationError, PermissionDenied

from flowback.group.models import Group, GroupUser, WorkGroup, WorkGroupUser, GroupPermissions
from flowback.user.models import User


def group_user_permissions(*,
                           user: Union[User, int] = None,
                           group: Union[Group, int] = None,
                           group_user: GroupUser | int = None,
                           permissions: Union[list[str], str] = None,
                           work_group: WorkGroup | int = None,
                           raise_exception: bool = True,
                           allow_admin: bool = False) -> Union[GroupUser, bool]:
    permissions = permissions or []
    work_group_moderator_check = False

    # Set up initial values for the function
    if isinstance(user, int):
        user = User.objects.get(id=user, is_active=True)

    if isinstance(group, int):
        group = Group.objects.get(id=group, active=True)

    if isinstance(permissions, str):
        permissions = [permissions]

    if isinstance(work_group, int):
        work_group = WorkGroup.objects.get(id=work_group)

    if isinstance(group_user, int):
        group_user = GroupUser.objects.get(id=group_user, active=True)

    if group_user:
        if not group_user.active:
            raise ValidationError('Group user is not active')

    if user and group:
        group_user = GroupUser.objects.get(user=user, group=group, active=True)

    elif user and work_group:
        group_user = GroupUser.objects.get(group=work_group.group, user=user, active=True)

    elif not group_user:
        raise Exception('group_user_permissions is missing appropiate parameters')

    # Logic behind checking permissions
    admin = group_user.is_admin
    user_permissions = (model_to_dict(group_user.permission)
                        if group_user.permission
                        else model_to_dict(group_user.group.default_permission))

    # Check if admin permission is present
    if 'admin' in permissions:
        if group_user.is_admin or group_user.group.created_by == group_user.user or group_user.user.is_superuser:
            allow_admin = True

    # Check if creator permission is present
    if 'creator' in permissions:
        if group_user.group.created_by == group_user.user or group_user.user.is_superuser:
            allow_admin = True

    # Check if work_group_moderator is present, mark as true and check further down
    if 'work_group_moderator' in permissions:
        work_group_moderator_check = True

    validated_permissions = any([user_permissions.get(key, False) for key in permissions]) or not permissions
    if not validated_permissions and not (admin and allow_admin):
        if raise_exception:
            raise PermissionDenied(
                f'Requires one of following permissions: {", ".join(permissions)})')
        else:
            return False

    if work_group and not admin:
        try:
            work_group_user = WorkGroupUser.objects.get(group_user=group_user, work_group=work_group)

        except WorkGroupUser.DoesNotExist:
            raise PermissionDenied("Requires work group membership")

        if work_group_moderator_check and not work_group_user.is_moderator:
            raise PermissionDenied("Requires work group moderator permission")

    return group_user


class BaseGroupPermissionsFilter(django_filters.FilterSet):
    class Meta:
        model = GroupPermissions
        fields = dict(id=['exact'], role_name=['exact', 'icontains'])


def group_permissions_list(*, group: int, fetched_by: User, filters=None):
    group_user_permissions(user=fetched_by, group=group)
    filters = filters or {}
    qs = GroupPermissions.objects.filter(author_id=group).all()
    return BaseGroupPermissionsFilter(filters, qs).qs
