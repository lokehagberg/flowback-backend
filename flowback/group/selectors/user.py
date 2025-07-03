import django_filters
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F, Q

from flowback.comment.selectors import comment_list
from flowback.common.services import get_object

from flowback.group.models import GroupUser, GroupUserInvite, GroupUserDelegator, GroupUserDelegatePool
from flowback.group.selectors.permission import group_user_permissions
from flowback.user.models import User


class BaseGroupUserFilter(django_filters.FilterSet):
    username__icontains = django_filters.CharFilter(field_name='user__username', lookup_expr='icontains')
    delegate_pool_id = django_filters.NumberFilter(),
    is_delegate = django_filters.BooleanFilter(field_name='delegate_pool_id', lookup_expr='isnull', exclude=True)

    class Meta:
        model = GroupUser
        fields = dict(id=['exact'],
                      user_id=['exact'],
                      is_admin=['exact'],
                      permission=['in'])


def group_user_list(*, group_id: int, fetched_by: User, filters=None):
    group_user_permissions(user=fetched_by, group=group_id)
    filters = filters or {}
    qs = GroupUser.objects.filter(group_id=group_id,
                                  active=True,
                                  ).annotate(delegate_pool_id=F('groupuserdelegate__pool_id'),
                                             work_groups=ArrayAgg('workgroupuser__work_group__name')).all()
    return BaseGroupUserFilter(filters, qs).qs


class BaseGroupUserInviteFilter(django_filters.FilterSet):
    username__icontains = django_filters.CharFilter(field_name='user__username', lookup_expr='icontains')

    class Meta:
        model = GroupUserInvite
        fields = ['user', 'group']


def group_user_invite_list(*, group: int, fetched_by: User, filters=None):
    if group:
        group_user_permissions(user=fetched_by, group=group, permissions=['invite_user', 'admin'])
        qs = GroupUserInvite.objects.filter(group_id=group).all()

    else:
        qs = GroupUserInvite.objects.filter(user=fetched_by).all()

    filters = filters or {}
    return BaseGroupUserInviteFilter(filters, qs).qs


class BaseGroupUserDelegateFilter(django_filters.FilterSet):
    delegate_id = django_filters.NumberFilter()
    delegate_user_id = django_filters.NumberFilter(field_name='delegate__user_id')
    delegate_name__icontains = django_filters.CharFilter(field_name='delegate__user__username__icontains')
    tag_id = django_filters.NumberFilter(field_name='tags__id')
    tag_name = django_filters.CharFilter(field_name='tags__name')
    tag_name__icontains = django_filters.CharFilter(field_name='tags__tag_name', lookup_expr='icontains')

    class Meta:
        model = GroupUserDelegator
        fields = ['delegate_id']


def group_user_delegate_list(*, group: int, fetched_by: User, filters=None):
    filters = filters or {}
    fetched_by = group_user_permissions(user=fetched_by, group=group)
    query = Q(group_id=group, delegator_id=fetched_by)

    qs = GroupUserDelegator.objects.filter(query).all()
    return BaseGroupUserDelegateFilter(filters, qs).qs


def group_delegate_pool_comment_list(*, fetched_by: User, delegate_pool_id: int, filters=None):
    filters = filters or {}
    delegate_pool = get_object(GroupUserDelegatePool, id=delegate_pool_id)
    group_user_permissions(user=fetched_by, group=delegate_pool.group)

    return comment_list(fetched_by=fetched_by, comment_section_id=delegate_pool.comment_section.id, filters=filters)
