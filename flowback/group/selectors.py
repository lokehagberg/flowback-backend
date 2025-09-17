# TODO groups, groupusers, groupinvites, groupuserinvites,
#  groupdefaultpermission, grouppermissions, grouptags, groupuserdelegates
import django_filters
from django.db.models import Q
from flowback.common.services import get_object
from flowback.user.models import User
from flowback.group.models import Group, GroupUser, GroupUserInvite
from rest_framework.exceptions import ValidationError


def group_user_permissions(*, group: id, user: User, permissions: list[str] = None, raise_exception=True):
    permissions = permissions or []
    user_permissions = get_object(GroupUser, 'User is not in group', group=group, user=user).permission.values()
    failed_permissions = [key for key in permissions if user_permissions[key] is False]
    if failed_permissions:
        if raise_exception:
            raise ValidationError('Permission denied')
        else:
            return False

    return True


class BaseGroupFilter(django_filters.FilterSet):
    class Meta:
        model = Group
        fields = ('id', 'name__icontains', 'direct_join', 'group_user__user')


class BaseGroupUserFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(field_name='user__username')

    class Meta:
        model = GroupUser
        fields = ('user_id', 'username__icontains', 'is_delegate', 'is_admin', 'permission__in')


class BaseGroupUserInviteFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(field_name='user__username')

    class Meta:
        model = GroupUser
        fields = ('user_id', 'username__icontains')


def group_get_visible_for(user: User):
    query = Q(public=True) | Q(Q(public=False) | Q(group_user__user=user))
    return Group.objects.filter(query)


def group_list(*, fetched_by: User, filters=None):
    filters = filters or {}
    qs = group_get_visible_for(user=fetched_by).all()
    return BaseGroupFilter(filters, qs).qs


def group_user_list(*, group: id, fetched_by: User, filters=None):
    group_user_permissions(group=group, user=fetched_by)
    filters = filters or {}
    qs = GroupUser.objects.filter(group_id=group).all()
    return BaseGroupUserFilter(filters, qs).qs


def group_user_invite_list(*, group: id, fetched_by: User, filters=None):
    group_user_permissions(group=group, user=fetched_by, permissions=['invite_user'])
    filters = filters or {}
    qs = GroupUserInvite.objects.filter(group_id=group).all()
    return BaseGroupUserFilter(filters, qs).qs
