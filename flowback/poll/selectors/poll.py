from typing import Union

import django_filters
from django.db import models
from django.db.models import Q, Exists, OuterRef, Count, Sum, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from flowback.comment.models import Comment
from flowback.common.filters import ExistsFilter
from flowback.common.filters import NumberInFilter
from flowback.group.models import Group
from flowback.poll.models import Poll, PollPriority
from flowback.user.models import User
from flowback.group.selectors import group_user_permissions


class BasePollFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('start_date', 'start_date_asc'),
                                                     ('-start_date', 'start_date_desc'),
                                                     ('end_date', 'end_date_asc'),
                                                     ('-end_date', 'end_date_desc'),
                                                     ('priority', 'priority_asc'),
                                                     ('-priority', 'priority_desc')))
    start_date = django_filters.DateTimeFilter()
    end_date = django_filters.DateTimeFilter()
    description = django_filters.CharFilter(field_name='description', lookup_expr='icontains')
    has_attachments = ExistsFilter(field_name='attachments')
    tag_name = django_filters.CharFilter(lookup_expr=['exact', 'icontains'], field_name='tag__name')
    author_ids = NumberInFilter(field_name='created_by__user_id')
    user_priority__gte = django_filters.NumberFilter(field_name='user_priority', lookup_expr='gte')
    user_priority__lte = django_filters.NumberFilter(field_name='user_priority', lookup_expr='lte')

    class Meta:
        model = Poll
        fields = dict(id=['exact', 'in'],
                      created_by=['exact'],
                      title=['exact', 'icontains'],
                      description=['exact', 'icontains'],
                      poll_type=['exact'],
                      public=['exact'],
                      tag=['exact'],
                      status=['exact'],
                      pinned=['exact'])


# TODO order_by(pinned, param)
def poll_list(*, fetched_by: User, group_id: Union[int, None], filters=None):
    filters = filters or {}

    if group_id:
        group_user_permissions(group=group_id, user=fetched_by)
        qs = Poll.objects.filter(created_by__group_id=group_id) \
            .annotate(total_comments=Count('comment_section__comment', filters=dict(active=True)),
                      priority=Sum('pollpriority__score', output_field=models.IntegerField(), default=0),
                      user_priority=Subquery(
                          PollPriority.objects.filter(poll=OuterRef('id'),
                                                      group_user__user=fetched_by).values('score'),
                          output_field=models.IntegerField())).all()

    else:
        joined_groups = Group.objects.filter(id=OuterRef('created_by__group_id'), groupuser__user__in=[fetched_by])
        qs = Poll.objects.filter(
            (Q(created_by__group__groupuser__user__in=[fetched_by]) |
             Q(public=True) & ~Q(created_by__group__groupuser__user__in=[fetched_by])
             ) & Q(start_date__lte=timezone.now())
        ).annotate(group_joined=Exists(joined_groups),
                   priority=Sum('pollpriority__score', output_field=models.IntegerField(), default=0),
                   user_priority=Subquery(
                       PollPriority.objects.filter(poll=OuterRef('id'),
                                                   group_user__user=fetched_by).values('score'),
                       output_field=models.IntegerField()),
                   total_comments=Count('comment_section__comment', filters=dict(active=True))).all()

    return BasePollFilter(filters, qs).qs
