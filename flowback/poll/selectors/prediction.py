import django_filters
from django.db import models
from django.db.models import Avg, When, F, Case, Count, Q, Exists, Subquery, OuterRef
from django.db.models.fields.related import RelatedField
from django.db.models.lookups import LessThan
from django.utils import timezone

from flowback.common.filters import NumberInFilter
from flowback.group.selectors import group_user_permissions
from flowback.poll.models import PollPredictionStatement, PollPredictionBet, PollPredictionStatementVote, \
    PollPredictionStatementSegment
from flowback.user.models import User


class BasePollPredictionStatementFilter(django_filters.FilterSet):
    proposals = NumberInFilter(field_name='pollpredictionstatementsegment__proposal')
    title = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    created_by_id = django_filters.NumberFilter(field_name='created_by__user_id', lookup_expr='exact')
    user_prediction_bet__exists = django_filters.BooleanFilter(lookup_expr='isnull', exclude=True)
    user_vote__exists = django_filters.BooleanFilter(lookup_expr='isnull', exclude=True)

    class Meta:
        model = PollPredictionStatement
        fields = dict(id=['exact'],
                      poll_id=['exact'])


def poll_prediction_statement_list(*, fetched_by: User, group_id: int, filters=None):
    filters = filters or {}
    group_user = group_user_permissions(user=fetched_by, group=group_id)

    # Annotations
    score = Case(When(LessThan(F('end_date'), timezone.now()),
                 then=Avg('pollpredictionbet__score')),
                 default=None, output_field=models.FloatField())
    vote_yes = Count(F('pollpredictionstatementvote'), filter=Q(pollpredictionstatementvote__vote=True))
    vote_no = Count(F('pollpredictionstatementvote'), filter=Q(pollpredictionstatementvote__vote=False))
    user_prediction_bet = PollPredictionBet.objects.filter(prediction_statement=OuterRef('pk'),
                                                           created_by=group_user).values('score')
    user_vote = PollPredictionStatementVote.objects.filter(prediction_statement=OuterRef('pk'),
                                                           created_by=group_user).values('vote')

    qs = PollPredictionStatement.objects.filter(poll__created_by__group_id=group_id
                                                ).annotate(score=score,
                                                           vote_yes=vote_yes,
                                                           vote_no=vote_no,
                                                           user_prediction_bet=user_prediction_bet,
                                                           user_prediction_statement_vote=user_vote
                                                           ).all()

    return BasePollPredictionStatementFilter(filters, qs).qs


# poll_prediction_list
class BasePollPredictionBetFilter(django_filters.FilterSet):
    created_by_id = django_filters.NumberFilter(field_name='created_by__user_id')

    class Meta:
        model = PollPredictionBet
        fields = dict(id=['exact'],
                      prediction_statement_id=['exact'],
                      score=['exact', 'lt', 'gt'],
                      created_at=['lt', 'gt'])


def poll_prediction_bet_list(*, fetched_by: User, group_id: int = None, filters=None):
    filters = filters or {}
    group_user_permissions(user=fetched_by, group=group_id)

    qs = PollPredictionBet.objects.filter(prediction_statement__created_by__group_id=group_id,
                                          created_by__user=fetched_by).all()
    return BasePollPredictionBetFilter(filters, qs).qs
