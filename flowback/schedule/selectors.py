# Schedule Event List (with multiple schedule id support)
import django_filters
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import OuterRef, Subquery, Exists

from flowback.common.filters import NumberInFilter
from flowback.schedule.models import ScheduleEvent, ScheduleEventSubscription, ScheduleTagSubscription, Schedule
from flowback.user.models import User


class ScheduleEventBaseFilter(django_filters.FilterSet):
    ids = NumberInFilter(field_name='id')
    schedule_origin_name = django_filters.CharFilter(field_name='schedule__content_type__model',
                                                     lookup_expr='iexact')
    schedule_origin_id = NumberInFilter(field_name='schedule__object_id')
    origin_name = django_filters.CharFilter(field_name='content_type.model', lookup_expr='iexact')
    origin_ids = NumberInFilter(field_name='object_id')
    schedule_ids = NumberInFilter(field_name='schedule_id')
    title = django_filters.CharFilter(lookup_expr='iexact')
    description = django_filters.CharFilter(lookup_expr='icontains')
    active = django_filters.BooleanFilter()
    tag_ids = NumberInFilter(field_name='tag_id')
    assignee_user_ids = NumberInFilter(field_name='assignees__user__id')
    repeat_frequency__isnull = django_filters.BooleanFilter(field_name='repeat_frequency', lookup_expr='isnull')
    user_tags = django_filters.CharFilter(lookup_expr='iexact')
    subscribed = django_filters.BooleanFilter()
    locked = django_filters.BooleanFilter()
    tag_name = django_filters.CharFilter(lookup_expr=['exact', 'icontains'], field_name='tag__name')

    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc'),
                                                     ('start_date', 'start_date_asc'),
                                                     ('-start_date', 'start_date_desc'),
                                                     ('end_date', 'end_date_asc'),
                                                     ('-end_date', 'end_date_desc')))

    class Meta:
        model = ScheduleEvent
        fields = dict(start_date=['lt', 'gt', 'exact'],
                      end_date=['lt', 'gt', 'exact'])


def schedule_event_list(*, user: User, filters=None):
    filters = filters or {}
    subscription_qs = ScheduleEventSubscription.objects.filter(event_id=OuterRef('id'),
                                                               schedule_user__user=user)

    subscribed_qs = ScheduleTagSubscription.objects.filter(schedule_user__user=user,
                                                           schedule_tag=OuterRef('tag'))

    qs = ScheduleEvent.objects.filter(
        scheduleeventsubscription__schedule_user__user=user
    ).annotate(reminders=Subquery(subscription_qs.values('reminders')),
               user_tags=Subquery(subscription_qs.values('tags')),
               locked=Subquery(subscription_qs.values('locked')),
               subscribed=Exists(subscribed_qs)).all()

    return ScheduleEventBaseFilter(filters, qs).qs


class ScheduleBaseFilter(django_filters.FilterSet):
    ids = NumberInFilter(field_name='id')
    origin_name = django_filters.CharFilter(field_name='content_type__model', lookup_expr='iexact')
    origin_ids = NumberInFilter(field_name='object_id')
    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc'),
                                                     ('content_type__model', 'origin_name_asc'),
                                                     ('-content_type__model', 'origin_name_desc')))

    class Meta:
        model = Schedule
        fields = dict(id=['exact'])


# Schedule list (incl. info about subscriptions, reminders, user tags and tags)
def schedule_list(*, user: User, filters=None):
    filters = filters or {}
    qs = Schedule.objects.filter(
        scheduleuser__user=user
    ).annotate(available_tags=ArrayAgg('scheduletag__name', distinct=True)).all()

    return ScheduleBaseFilter(filters, qs).qs
