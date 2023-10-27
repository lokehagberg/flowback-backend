import django_filters
from django.db import models
from django.db.models import OuterRef, Subquery, Count

from flowback.common.services import get_object
from flowback.group.selectors import group_user_permissions
from flowback.poll.models import PollAreaStatement, PollAreaStatementVote, Poll
from flowback.user.models import User


class BasePollAreaStatementFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc'),
                                                     ('score', 'score_asc'),
                                                     ('-score', 'score_desc')))

    vote = django_filters.BooleanFilter()
    tag = django_filters.CharFilter(field_name='pollareastatementsegment__tag__name',
                                    lookup_expr='iexact')


def poll_area_statement_list(*, user: User, poll_id: int, filters=None):
    filters = filters or {}
    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(user=user, group=poll.created_by.group)

    user_votes = PollAreaStatementVote.objects.filter(created_by=group_user,
                                                      poll_area_statement=OuterRef('pk')).values('vote')
    qs = PollAreaStatement.objects.filter(poll=poll).annotate(vote=Subquery(user_votes,
                                                                            output_field=models.BooleanField()))

    return BasePollAreaStatementFilter(filters, qs).qs
