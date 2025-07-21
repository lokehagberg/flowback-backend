import django_filters
from django.db.models import Exists, OuterRef, Subquery, Count, Q
from django.db.models.functions import Coalesce
from rest_framework.exceptions import PermissionDenied

from flowback.group.models import WorkGroup, WorkGroupUser, WorkGroupUserJoinRequest, Group
from flowback.group.selectors.permission import group_user_permissions
from flowback.user.models import User


class BaseWorkGroupFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc'),
                                                     ('name', 'name_asc'),
                                                     ('-name', 'name_desc')))
    joined = django_filters.BooleanFilter()

    class Meta:
        model = WorkGroup
        fields = dict(id=['exact'],
                      name=['exact', 'icontains'])


def work_group_list(*, group_id: int, fetched_by: User, filters=None):
    filters = filters or {}
    group_user = group_user_permissions(user=fetched_by, group=group_id)

    qs = WorkGroup.objects.filter(group_id=group_id).annotate(
        joined=Exists(
            WorkGroupUser.objects.filter(
                work_group=OuterRef('pk'),
                group_user=group_user
            )
        ),
        requested_access=Exists(
            WorkGroupUserJoinRequest.objects.filter(
                work_group=OuterRef('pk'),
                group_user=group_user
            )
        ),
        member_count=Coalesce(Subquery(
            WorkGroupUser.objects.filter(work_group=OuterRef('pk'))
            .values('work_group')
            .annotate(count=Count('id'))
            .values('count')[:1]), 0)
    )

    return BaseWorkGroupFilter(filters, qs).qs


class BaseWorkGroupUserFilter(django_filters.FilterSet):
    user_id = django_filters.CharFilter(field_name='group_user__user_id', lookup_expr='exact')
    username = django_filters.CharFilter(field_name='group_user__user__username', lookup_expr='icontains')

    class Meta:
        model = WorkGroupUser
        fields = dict(id=['exact'],
                      group_user_id=['exact'])


def work_group_user_list(*, work_group_id: int, fetched_by: User, filters=None):
    filters = filters or {}

    # Won't need to check group_user_permission if the user is already in the work group
    group_user = group_user_permissions(user=fetched_by, work_group=work_group_id, allow_admin=True)

    qs = WorkGroupUser.objects.filter(work_group_id=work_group_id
                                      ).annotate(joined=Q(group_user__in=[group_user]))

    return BaseWorkGroupFilter(filters, qs).qs


class BaseWorkGroupUserJoinRequestFilter(django_filters.FilterSet):
    user_id = django_filters.NumberFilter(field_name='group_user__user_id', lookup_expr='exact')
    username = django_filters.NumberFilter(field_name='group_user__user__username', lookup_expr='icontains')
    work_group_id = django_filters.NumberFilter(field_name='work_group_id', lookup_expr='exact')

    class Meta:
        model = WorkGroupUserJoinRequest
        fields = dict(id=['exact'],
                      group_user_id=['exact'])


def work_group_user_join_request_list(*, group_id: int, fetched_by: User, filters=None):
    filters = filters or {}

    group = Group.objects.get(id=group_id)

    # Won't need to check if group_user is in work_group due to admin/moderator requirement
    group_user_is_admin = group_user_permissions(user=fetched_by,
                                                 group=group,
                                                 permissions=['admin'],
                                                 raise_exception=False)

    if not group_user_is_admin:
        work_group_filter = WorkGroup.objects.filter(id=OuterRef('work_group_id'),
                                                     work_group__group_id=group_id,
                                                     workgroupuser__group_user__user__in=[fetched_by],
                                                     workgroupuser__is_moderator=True)

        qs = WorkGroupUserJoinRequest.objects.filter(work_group_id__in=Subquery(work_group_filter))

    else:
        qs = WorkGroupUserJoinRequest.objects.filter(work_group__group_id=group_id)

    return BaseWorkGroupFilter(filters, qs).qs
