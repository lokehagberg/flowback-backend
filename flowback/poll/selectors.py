from typing import Union

import django_filters
from django.db.models import Q

from flowback.common.services import get_object
from flowback.poll.models import Poll, PollProposal, PollVotingTypeRanking, PollDelegateVoting, PollVoting
from flowback.user.models import User
from flowback.group.selectors import group_user_permissions


class BasePollFilter(django_filters.FilterSet):
    start_date = django_filters.DateFromToRangeFilter()
    end_date = django_filters.DateFromToRangeFilter()
    tag_name = django_filters.CharFilter(lookup_expr=['exact', 'icontains'], field_name='tag__name')

    class Meta:
        model = Poll
        fields = dict(id=['exact'],
                      created_by=['exact'],
                      title=['exact', 'icontains'],
                      poll_type=['exact'],
                      public=['exact'],
                      tag=['exact'],
                      finished=['exact'])


class BasePollProposalFilter(django_filters.FilterSet):
    class Meta:
        model = PollProposal
        fields = dict(id=['exact'],
                      created_by=['exact'],
                      title=['exact', 'icontains'])


class BasePollVoteRankingFilter(django_filters.FilterSet):
    delegate_pool_id = django_filters.NumberFilter(field_name='author_delegate__created_by')
    delegate_user_id = django_filters.NumberFilter(
        field_name='author_delegate__created_by__groupuserdelegate__group_user__user_id')

    class Meta:
        model = PollVotingTypeRanking
        fields = dict(proposal=['exact'])


class BasePollDelegateVotingFilter(django_filters.FilterSet):
    class Meta:
        model = PollDelegateVoting
        fields = dict(created_by=['exact'])


def poll_list(*, fetched_by: User, group_id: Union[int, None], filters=None):
    group_user_permissions(group=group_id, user=fetched_by)
    filters = filters or {}
    if group_id:
        qs = Poll.objects.filter(created_by__group_id=group_id).all()

    else:
        qs = Poll.objects.filter(Q(created_by__group__groupuser__in=[fetched_by]) | Q(public=True)).all()

    return BasePollFilter(filters, qs).qs


def poll_proposal_list(*, fetched_by: User, group_id: int, poll_id: int, filters=None):
    poll = get_object(Poll, id=poll_id)
    if not poll.public:
        group_user_permissions(group=group_id, user=fetched_by)

    filters = filters or {}
    qs = PollProposal.objects.filter(created_by__group_id=group_id, poll=poll).all()
    return BasePollProposalFilter(filters, qs).qs


def poll_vote_list(*, fetched_by: User, group_id: int, poll_id: int, delegates: bool = False, filters=None):
    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(group=group_id, user=fetched_by)
    filters = filters or {}

    if poll.poll_type == Poll.PollType.RANKING:
        if delegates:
            qs = PollVotingTypeRanking.objects.filter(proposal__poll=poll,
                                                      author_delegate__isnull=False).order_by('-priority').all()
        else:
            qs = PollVotingTypeRanking.objects.filter(proposal__poll=poll,
                                                      author__created_by=group_user).order_by('-priority').all()

        return BasePollVoteRankingFilter(filters, qs).qs


def poll_delegates_list(*, fetched_by: User, group_id: int, poll_id: int, filters=None):
    poll = get_object(Poll, id=poll_id)
    group_user_permissions(group=group_id, user=fetched_by)
    filters = filters or {}
    qs = PollDelegateVoting.objects.filter(poll=poll).all()
    return BasePollDelegateVotingFilter(filters, qs).qs
