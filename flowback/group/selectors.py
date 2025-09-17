# TODO groups, groupusers, groupinvites, groupuserinvites,
#  groupdefaultpermission, grouppermissions, grouptags, groupuserdelegates
import django_filters
from typing import Union
from django.db.models import Q, Exists, OuterRef, Count
from django.forms import model_to_dict

from flowback.common.services import get_object
from flowback.user.models import User
from flowback.group.models import Group, GroupUser, GroupUserInvite, GroupPermissions, GroupTags, GroupUserDelegator, \
    GroupUserDelegatePool
from rest_framework.exceptions import ValidationError


def group_default_permissions(*, group: int):
    group = get_object(Group, id=group)
    if group.default_permission:
        return model_to_dict(group.default_permission)

    fields = GroupPermissions._meta.get_fields()
    fields = [field for field in fields if not field.auto_created
              and field.name not in ['created_at', 'updated_at', 'role_name', 'author']]

    defaults = dict()
    for field in fields:
        defaults[field.name] = field.default

    return defaults


def group_user_permissions(*,
                           group: int,
                           user: Union[User, int],
                           permissions: list[str] = None,
                           raise_exception: bool = True) -> Union[GroupUser, bool]:



    if type(user) == int:
        user = get_object(User, id=user)
    permissions = permissions or []
    requires_permissions = bool(permissions)  # Avoids authentication if all permissions are removed before check
    user = get_object(GroupUser, 'User is not in group', group=group, user=user)
    perobj = GroupPermissions()
    user_permissions = model_to_dict(user.permission) if user.permission else group_default_permissions(group=group)

    # Check if admin permission is present
    if 'admin' in permissions:
        if user.is_admin or user.group.created_by == user.user or user.user.is_superuser:
            return user

        permissions.remove('admin')

    # Check if creator permission is present
    if 'creator' in permissions:
        if user.group.created_by == user.user or user.user.is_superuser:
            return user

        permissions.remove('creator')

    failed_permissions = [key for key in permissions if user_permissions[key] is False]
    if failed_permissions or (requires_permissions and failed_permissions):
        if raise_exception:
            raise ValidationError('Permission denied')
        else:
            return False

    return user


class BaseGroupFilter(django_filters.FilterSet):
    joined = django_filters.BooleanFilter(lookup_expr='exact')

    class Meta:
        model = Group
        fields = dict(id=['exact'],
                      name=['exact', 'icontains'],
                      direct_join=['exact'])


class BaseGroupUserFilter(django_filters.FilterSet):
    username__icontains = django_filters.CharFilter(field_name='user__username', lookup_expr='icontains')
    delegate = django_filters.BooleanFilter(field_name='delegate')

    class Meta:
        model = GroupUser
        fields = dict(id=['exact'],
                      user_id=['exact'],
                      is_admin=['exact'],
                      permission=['in'])


class BaseGroupUserInviteFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(field_name='user__username')
    username__icontains = django_filters.CharFilter(field_name='user__username', lookup_expr='icontains')

    class Meta:
        model = GroupUser
        fields = ['user']


class BaseGroupPermissionsFilter(django_filters.FilterSet):
    class Meta:
        model = GroupPermissions
        fields = dict(id=['exact'], role_name=['exact', 'icontains'])


class BaseGroupTagsFilter(django_filters.FilterSet):
    class Meta:
        model = GroupTags
        fields = dict(id=['exact'],
                      tag_name=['exact', 'icontains'],
                      active=['exact'])


class BaseGroupUserDelegatePoolFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter()
    delegate_id = django_filters.NumberFilter(field_name='groupuserdelegate__id')
    group_user_id = django_filters.NumberFilter(field_name='groupuserdelegate__group_user_id')


class BaseGroupUserDelegateFilter(django_filters.FilterSet):
    delegate_id = django_filters.NumberFilter()
    delegate_user_id = django_filters.NumberFilter(field_name='delegate__user_id')
    delegate_name__icontains = django_filters.CharFilter(field_name='delegate__user__username__icontains')
    tag_id = django_filters.NumberFilter(field_name='tags__tag_id')
    tag_name = django_filters.CharFilter(field_name='tags__tag_name')
    tag_name__icontains = django_filters.CharFilter(field_name='tags__tag_name', lookup_expr='icontains')

    class Meta:
        model = GroupUserDelegator
        fields = ['delegate_id']


def _group_get_visible_for(user: User):
    query = Q(public=True) | Q(Q(public=False) & Q(groupuser__user__in=[user]))
    return Group.objects.filter(query)


def group_list(*, fetched_by: User, filters=None):
    filters = filters or {}
    joined_groups = Group.objects.filter(id=OuterRef('pk'), groupuser__user__in=[fetched_by])
    qs = _group_get_visible_for(user=fetched_by).annotate(joined=Exists(joined_groups),
                                                          member_count=Count('groupuser')).order_by('created_at').all()
    qs = BaseGroupFilter(filters, qs).qs
    return qs


def group_detail(*, fetched_by: User, group_id: int):
    group_user = group_user_permissions(group=group_id, user=fetched_by)
    return Group.objects.annotate(member_count=Count('groupuser')).get(id=group_user.group.id)


def group_user_list(*, group: int, fetched_by: User, filters=None):
    group_user_permissions(group=group, user=fetched_by)
    filters = filters or {}
    is_delegate = GroupUser.objects.filter(group_id=group, groupuserdelegate__group_user=OuterRef('pk'),
                                           groupuserdelegate__group=OuterRef('group'))
    qs = GroupUser.objects.filter(group_id=group).annotate(delegate=Exists(is_delegate)).all()
    return BaseGroupUserFilter(filters, qs).qs


def group_user_delegate_pool_list(*, group: int, fetched_by: User, filters=None):
    group_user_permissions(group=group, user=fetched_by)
    filters = filters or {}
    qs = GroupUserDelegatePool.objects.filter(group=group).all()
    return BaseGroupUserDelegatePoolFilter(filters, qs).qs


def group_user_invite_list(*, group: int, fetched_by: User, filters=None):
    group_user_permissions(group=group, user=fetched_by, permissions=['invite_user'])
    filters = filters or {}
    qs = GroupUserInvite.objects.filter(group_id=group).all()
    return BaseGroupUserFilter(filters, qs).qs


def group_permissions_list(*, group: int, fetched_by: User, filters=None):
    group_user_permissions(group=group, user=fetched_by)
    filters = filters or {}
    qs = GroupPermissions.objects.filter(author_id=group).all()
    return BaseGroupPermissionsFilter(filters, qs).qs


def group_tags_list(*, group: int, fetched_by: User, filters=None):
    filters = filters or {}
    group_user_permissions(group=group, user=fetched_by)
    query = Q(group_id=group, active=True)
    if group_user_permissions(group=group, user=fetched_by, permissions=['admin'], raise_exception=False):
        query = Q(group_id=group)

    qs = GroupTags.objects.filter(query).all()
    return BaseGroupTagsFilter(filters, qs).qs


def group_user_delegate_list(*, group: int, fetched_by: User, filters=None):
    filters = filters or {}
    fetched_by = group_user_permissions(group=group, user=fetched_by)
    query = Q(group_id=group, delegator_id=fetched_by)

    qs = GroupUserDelegator.objects.filter(query).all()
    return BaseGroupUserDelegateFilter(filters, qs).qs
