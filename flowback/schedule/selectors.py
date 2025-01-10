# Schedule Event List (with multiple schedule id support)
import django_filters
from django.db.models import Q, F

from flowback.common.filters import NumberInFilter
from flowback.group.models import WorkGroupUser
from flowback.schedule.models import ScheduleEvent, ScheduleSubscription


class ScheduleEventBaseFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='iexact')
    work_group_ids = NumberInFilter()
    assignee_ids = NumberInFilter(field_name='assignees__id')
    repeat_frequency__isnull = django_filters.BooleanFilter(field_name='repeat_frequency', lookup_expr='isnull')

    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc'),
                                                     ('start_date', 'start_date_asc'),
                                                     ('-start_date', 'start_date_desc'),
                                                     ('end_date', 'end_date_asc'),
                                                     ('-end_date', 'end_date_desc')))


    class Meta:
        model = ScheduleEvent
        fields = dict(start_date=['lt', 'gt', 'exact'],
                      end_date=['lt', 'gt', 'exact'],
                      origin_name=['exact'],
                      origin_id=['exact'])


def schedule_event_list(*, schedule_id: int, group_user=None, filters=None):
    filters = filters or {}
    subquery = ScheduleSubscription.objects.filter(schedule_id=schedule_id).values_list('target_id')
    qs = ScheduleEvent.objects.filter(Q(schedule_id=schedule_id) | Q(schedule__in=subquery))

    if group_user is not None and not group_user.is_admin:
        work_group_ids = WorkGroupUser.objects.filter(group_user=group_user).values_list('work_group_id')
        qs = qs.exclude(Q(work_group__isnull=False) & ~Q(work_group_id__in=work_group_ids)).all()

    return ScheduleEventBaseFilter(filters, qs).qs
