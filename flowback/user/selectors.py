import django_filters
from django.db import models
from django.db.models import OuterRef, Q, Exists
from django_filters import FilterSet
from rest_framework.exceptions import ValidationError

from flowback.common.services import get_object
from flowback.group.models import Group, GroupUser, GroupThread
from flowback.poll.models import Poll
from flowback.schedule.selectors import schedule_event_list
from flowback.kanban.selectors import kanban_entry_list
from flowback.user.models import User
from backend.settings import env


class UserFilter(FilterSet):
    class Meta:
        model = User
        fields = {'id': ['exact'],
                  'username': ['exact', 'icontains']
                  }


def get_user(user: int):
    return get_object(User, id=user)


def user_schedule_event_list(*, fetched_by: User, filters=None):
    filters = filters or {}
    return schedule_event_list(schedule_id=fetched_by.schedule.id, filters=filters)


def user_kanban_entry_list(*, fetched_by: User, filters=None):
    filters = filters or {}
    return kanban_entry_list(kanban_id=fetched_by.kanban.id, filters=filters, subscriptions=True)


def user_list(*, fetched_by: User, filters=None):
    # Block access to this api for members, unless group admin or higher.
    if env('FLOWBACK_GROUP_ADMIN_USER_LIST_ACCESS_ONLY') \
            and not Group.objects.filter(created_by=fetched_by).exists() \
            and not GroupUser.objects.filter(user=fetched_by, is_admin=True) \
            and not (fetched_by.is_staff and fetched_by.is_superuser):
        raise ValidationError('User must be group admin or higher')

    filters = filters or {}
    qs = User.objects.all()
    return UserFilter(filters, qs).qs


class UserHomeFeedFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(lookup_expr='exact')
    created_by_id = django_filters.NumberFilter(lookup_expr='exact')
    title = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    related_model = django_filters.CharFilter(lookup_expr='exact')
    group_joined = django_filters.BooleanFilter(lookup_expr='exact')


def user_home_feed(*, fetched_by: User, filters=None):
    filters = filters or {}
    joined_groups = Group.objects.filter(id=OuterRef('created_by__group_id'), groupuser__user__in=[fetched_by])
    related_fields = ['id',
                      'created_by',
                      'created_at',
                      'updated_at',
                      'title',
                      'description',
                      'related_model',
                      'group_joined']

    # Thread

    q = (Q(created_by__group__groupuser__user__in=[fetched_by]) & Q(created_by__group__groupuser__active=True)
         | Q(created_by__group__public=True) & ~Q(created_by__group__groupuser__user__in=[fetched_by])
         | Q(created_by__group__public=True) & Q(created_by__group__groupuser__user__in=[fetched_by])
         & Q(created_by__group__groupuser__active=False))

    thread_qs = GroupThread.objects.filter(q)
    thread_qs = thread_qs.annotate(related_model=models.Value('group_thread', models.CharField()),
                                   group_joined=Exists(joined_groups))
    thread_qs = thread_qs.values(*related_fields)
    thread_qs = UserHomeFeedFilter(filters, thread_qs).qs

    # Poll
    poll_qs = Poll.objects.filter(q)
    poll_qs = poll_qs.annotate(related_model=models.Value('poll', models.CharField()),
                               group_joined=Exists(joined_groups))
    poll_qs = poll_qs.values(*related_fields)
    poll_qs = UserHomeFeedFilter(filters, poll_qs).qs

    qs = thread_qs.union(poll_qs).order_by('-created_at')

    return qs
