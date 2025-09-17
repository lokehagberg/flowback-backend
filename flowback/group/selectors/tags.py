import django_filters
from django.db import models
from django.db.models import Sum, Case, When, F, Q
from django.db.models.functions import Abs

from flowback.group.models import GroupTags
from flowback.group.selectors.permission import group_user_permissions
from flowback.poll.models import PollPredictionStatement
from flowback.poll.services.prediction import update_poll_prediction_statement_outcomes
from flowback.user.models import User


# print(f"Tag: {tags.first()}, "
#       f"Combined bets sum: {tags.first().sum_combined_bet}, "
#       f"Has bets: {tags.first().sum_outcome}, "
#       f"Outcome Sum: {tags.first().sum_outcome_score} "
#       f"IMAC: {tags.first().imac}")


class BaseGroupTagsFilter(django_filters.FilterSet):
    class Meta:
        model = GroupTags
        fields = dict(id=['exact'],
                      name=['exact', 'icontains'],
                      description=['exact', 'icontains'],
                      active=['exact'])


def group_tags_list(*, group_id: int, fetched_by: User = None, filters: dict = None):
    """
    Includes Interval Mean Absolute Correctness (imac) field:
    For every combined_bet & outcome in a given tag: abs(sum(combined_bet) – sum(outcome)) / N
    Where N is the number of predictions that had at least one bet
    """
    filters = filters or {}

    query = Q(group_id=group_id, active=True)

    if fetched_by:
        group_user = group_user_permissions(user=fetched_by, group=group_id)

        if group_user.is_admin:
            query = Q(group_id=group_id)

    tags = GroupTags.objects.filter(query)
    statements = list(PollPredictionStatement.objects.filter(poll__tag__group_id=group_id).values_list('id',
                                                                                                       flat=True))
    update_poll_prediction_statement_outcomes(statements)

    # Calculate IMAC
    tags = tags.annotate(sum_combined_bet=Sum('poll__pollpredictionstatement__combined_bet'),

                         sum_outcome=Sum(Case(When(poll__pollpredictionstatement__outcome=True, then=1), default=0)),

                         sum_outcome_score=Sum(Case(When(poll__pollpredictionstatement__outcome=True, then=1),
                                                    When(Q(poll__pollpredictionstatement__outcome=False)
                                                         | Q(poll__pollpredictionstatement__outcome=None), then=0),
                                                    output_field=models.DecimalField(max_digits=13, decimal_places=8))),

                         imac=Case(When(~Q(sum_outcome=0),
                                        then=1 - (Abs(F('sum_combined_bet') - F('sum_outcome_score'))) / F(
                                            'sum_outcome')),
                                   default=None, output_field=models.DecimalField(max_digits=13,
                                                                                  decimal_places=8,
                                                                                  null=True)))

    return BaseGroupTagsFilter(filters, tags).qs
