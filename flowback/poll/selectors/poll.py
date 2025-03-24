from typing import Union

import django_filters
from django.db.models import Q, Exists, OuterRef, Count, Subquery, Case, When, Value, CharField
from django.db.models.functions import Coalesce
from django.utils import timezone

from flowback.comment.models import Comment
from flowback.common.filters import ExistsFilter, NumberInFilter
from flowback.group.models import Group
from flowback.poll.models import Poll, PollPhaseTemplate, PollPredictionStatement
from flowback.user.models import User
from flowback.group.selectors import group_user_permissions


class BasePollFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('-pinned', 'pinned'),
                                                     ('start_date', 'start_date_asc'),
                                                     ('-start_date', 'start_date_desc'),
                                                     ('end_date', 'end_date_asc'),
                                                     ('-end_date', 'end_date_desc')))
    start_date = django_filters.DateTimeFilter()
    end_date = django_filters.DateTimeFilter()
    id_list = NumberInFilter(field_name='id')
    description = django_filters.CharFilter(field_name='description', lookup_expr='icontains')
    has_attachments = ExistsFilter(field_name='attachments')
    tag_name = django_filters.CharFilter(lookup_expr=['exact', 'icontains'], field_name='tag__name')
    tag_id = django_filters.NumberFilter(lookup_expr='exact', field_name='tag__id')
    phase = django_filters.CharFilter(lookup_expr='iexact')

    class Meta:
        model = Poll
        fields = dict(id=['exact'],
                      created_by=['exact'],
                      title=['exact', 'icontains'],
                      description=['exact', 'icontains'],
                      poll_type=['exact'],
                      public=['exact'],
                      status=['exact'],
                      pinned=['exact'],
                      start_date=['lt', 'gt'],
                      area_vote_end_date=['lt', 'gt'],
                      proposal_end_date=['lt', 'gt'],
                      prediction_statement_end_date=['lt', 'gt'],
                      prediction_bet_end_date=['lt', 'gt'],
                      delegate_vote_end_date=['lt', 'gt'],
                      vote_end_date=['lt', 'gt'],
                      end_date=['lt', 'gt'])


# TODO order_by(pinned, param)
def poll_list(*, fetched_by: User, group_id: Union[int, None], filters=None):
    filters = filters or {}

    # Determine phase by case qs
    poll_phase = Case(
        When(dynamic=True, end_date__lt=timezone.now(), then=Value('result')),
        When(end_date__lt=timezone.now(), then=Value('prediction_vote')),

        When(dynamic=True, vote_end_date__lte=timezone.now(), then=Value('result_default')),
        When(vote_end_date__lte=timezone.now(), then=Value('result')),

        When(delegate_vote_end_date__lte=timezone.now(), then=Value('vote')),
        When(prediction_bet_end_date__lte=timezone.now(), then=Value('delegate_vote')),
        When(prediction_statement_end_date__lte=timezone.now(), then=Value('prediction_bet')),
        When(proposal_end_date__lte=timezone.now(), then=Value('prediction_statement')),
        When(area_vote_end_date__lte=timezone.now(), then=Value('proposal')),

        When(dynamic=True,
             poll_type=Poll.PollType.SCHEDULE,
             start_date__lte=timezone.now(),
             then=Value('schedule')),
        When(dynamic=True, start_date__lte=timezone.now(), then=Value('dynamic')),
        When(start_date__lte=timezone.now(), then=Value('area_vote')),

        default=Value('waiting'),
        output_field=CharField()
    )

    if group_id:
        group_user_permissions(user=fetched_by, group=group_id)
        qs = Poll.objects.filter(created_by__group_id=group_id) \
            .annotate(phase=poll_phase,
                      total_comments=Coalesce(Subquery(
                          Comment.objects.filter(comment_section_id=OuterRef('comment_section_id'), active=True).values(
                              'comment_section_id').annotate(total=Count('*')).values('total')[:1]), 0),
                      total_proposals=Count('pollproposal', distinct=True),
                      total_predictions=Coalesce(Subquery(
                          PollPredictionStatement.objects.filter(poll_id=OuterRef('id')).values('poll_id')
                          .annotate(total=Count('*')).values('total')[:1]), 0)).all()

    else:
        joined_groups = Group.objects.filter(id=OuterRef('created_by__group_id'), groupuser__user__in=[fetched_by])
        qs = Poll.objects.filter(
            (Q(created_by__group__groupuser__user__in=[fetched_by]) & Q(created_by__group__groupuser__active=True)
             | Q(public=True) & ~Q(created_by__group__groupuser__user__in=[fetched_by])
             | Q(public=True) & Q(created_by__group__groupuser__user__in=[fetched_by]
                                  ) & Q(created_by__group__groupuser__active=False)
             ) & Q(start_date__lte=timezone.now())
        ).annotate(phase=poll_phase,
                   group_joined=Exists(joined_groups),
                   total_comments=Coalesce(Subquery(
                       Comment.objects.filter(comment_section_id=OuterRef('comment_section_id'), active=True).values(
                           'comment_section_id').annotate(total=Count('*')).values('total')[:1]), 0),
                   total_proposals=Count('pollproposal', distinct=True),
                   total_predictions=Coalesce(Subquery(
                       PollPredictionStatement.objects.filter(poll_id=OuterRef('id')).values('poll_id')
                       .annotate(total=Count('*')).values('total')[:1]), 0)).all()

    return BasePollFilter(filters, qs).qs


class BasePollPhaseTemplateFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc')))

    class Meta:
        model = PollPhaseTemplate
        fields = dict(created_by_group_user_id=['exact'],
                      name=['exact', 'icontains'],
                      poll_type=['exact'],
                      poll_is_dynamic=['exact'])


def poll_phase_template_list(*, fetched_by: User, group_id: int, filters=None):
    filters = filters or {}

    group_user_permissions(user=fetched_by, group=group_id)
    qs = PollPhaseTemplate.objects.filter(created_by_group_user__group_id=group_id).all()

    return BasePollPhaseTemplateFilter(filters, qs).qs
