from typing import Union

import django_filters
from django.db.models import Q, Exists, OuterRef, Count
from django.utils import timezone

from flowback.comment.models import Comment
from flowback.group.models import Group
from flowback.poll.models import Poll
from flowback.user.models import User
from flowback.group.selectors import group_user_permissions


class BasePollFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('start_date', 'start_date_asc'),
                                                     ('-start_date', 'start_date_desc'),
                                                     ('end_date', 'end_date_asc'),
                                                     ('-end_date', 'end_date_desc')))
    start_date = django_filters.DateTimeFilter()
    end_date = django_filters.DateTimeFilter()
    description = django_filters.CharFilter(field_name='description', lookup_expr='icontains')
    has_attachments = django_filters.BooleanFilter(method='has_attachments_filter')
    tag_name = django_filters.CharFilter(lookup_expr=['exact', 'icontains'], field_name='tag__name')
    author_id = django_filters.NumberFilter(field_name='created_by__user_id', lookup_expr='exact')
    author_id__in = django_filters.NumberFilter(field_name='created_by__user_id', lookup_expr='in')

    def has_attachments_filter(self, queryset, name, value):
        return queryset.filter(attachments__isnull=not value)

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
        qs = Poll.objects.filter(created_by__group_id=group_id)\
            .annotate(total_comments=Count('comment_section__comment', filters=dict(active=True))).all()

    else:
        joined_groups = Group.objects.filter(id=OuterRef('created_by__group_id'), groupuser__user__in=[fetched_by])
        qs = Poll.objects.filter(
            (Q(created_by__group__groupuser__user__in=[fetched_by]) |
             Q(public=True) & ~Q(created_by__group__groupuser__user__in=[fetched_by])
             ) & Q(start_date__lte=timezone.now())
        ).annotate(group_joined=Exists(joined_groups), total_comments=Count('comment_section__comment',
                                                                            filters=dict(active=True))).all()
    return BasePollFilter(filters, qs).qs
