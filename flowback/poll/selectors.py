from typing import Union

import django_filters
from django.db.models import Q
from django.utils import timezone

from flowback.common.services import get_object
from flowback.poll.models import Poll, PollProposal, PollVotingTypeRanking, PollDelegateVoting, PollVoting, \
    PollProposalTypeSchedule, PollVotingTypeForAgainst
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
    group = django_filters.NumberFilter(field_name='created_by__group_id', lookup_expr='exact')

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


class BasePollProposalScheduleFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(
        fields=(
            ('start_date', 'start_date_asc'),
            ('-start_date', 'start_date_desc'),
            ('end_date', 'end_date_asc'),
            ('-end_date', 'end_date_desc')
        )
    )

    group = django_filters.NumberFilter(field_name='created_by.group_id', lookup_expr='exact')
    start_date__lt = django_filters.DateTimeFilter(field_name='pollproposaltypeschedule.start_date', lookup_expr='lt')
    start_date__gt = django_filters.DateTimeFilter(field_name='pollproposaltypeschedule.start_date', lookup_expr='gt')
    end_date__lt = django_filters.DateTimeFilter(field_name='pollproposaltypeschedule.end_date', lookup_expr='lt')
    end_date__gt = django_filters.DateTimeFilter(field_name='pollproposaltypeschedule.end_date', lookup_expr='gt')
    poll_title = django_filters.CharFilter(field_name='poll.title', lookup_expr='exact')
    poll_title__icontains = django_filters.CharFilter(field_name='poll.title', lookup_expr='icontains')

    class Meta:
        model = PollProposal
        fields = dict(id=['exact'],
                      created_by=['exact'],
                      title=['exact', 'icontains'])


class BasePollVoteForAgainstFilter(django_filters.FilterSet):
    class Meta:
        model = PollVotingTypeForAgainst
        fields = dict(proposal=['exact'])


class BasePollDelegateVotingFilter(django_filters.FilterSet):
    class Meta:
        model = PollDelegateVoting
        fields = dict(created_by=['exact'])


def poll_list(*, fetched_by: User, group_id: Union[int, None], filters=None):
    filters = filters or {}
    if group_id:
        group_user_permissions(group=group_id, user=fetched_by)
        qs = Poll.objects.filter(created_by__group_id=group_id).all()

    else:
        qs = Poll.objects.filter((Q(created_by__group__groupuser__user__in=[fetched_by]) | Q(public=True))
                                 & Q(start_date__lte=timezone.now()))\
            .order_by('-id').distinct('id').all()

    return BasePollFilter(filters, qs).qs


def poll_proposal_list(*, fetched_by: User, group_id: int, poll_id: int, filters=None):
    if group_id and poll_id:
        poll = get_object(Poll, id=poll_id)
        if not poll.public:
            group_user_permissions(group=group_id, user=fetched_by)

        filters = filters or {}
        qs = PollProposal.objects.filter(created_by__group_id=group_id, poll=poll).order_by('-score').all()

        if poll.poll_type == Poll.PollType.SCHEDULE:
            return BasePollProposalScheduleFilter(filters, qs).qs
        else:
            return BasePollProposalFilter(filters, qs).qs


def poll_user_schedule_list(*, fetched_by: User, filters=None):
    filters = filters or {}
    qs = PollProposal.objects.filter(created_by__group__groupuser__user__in=[fetched_by],
                                     poll__poll_type=Poll.PollType.SCHEDULE,
                                     poll__finished=True).order_by('poll', 'score')\
        .distinct('poll').all()

    return BasePollProposalScheduleFilter(filters, qs).qs


def poll_vote_list(*, fetched_by: User, group_id: int, poll_id: int, delegates: bool = False, filters=None):
    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(group=group_id, user=fetched_by)
    filters = filters or {}

    # Ranking
    if poll.poll_type == Poll.PollType.RANKING:
        if delegates:
            qs = PollVotingTypeRanking.objects.filter(proposal__poll=poll,
                                                      author_delegate__isnull=False).order_by('-priority').all()
        else:
            qs = PollVotingTypeRanking.objects.filter(proposal__poll=poll,
                                                      author__created_by=group_user).order_by('-priority').all()

        return BasePollVoteRankingFilter(filters, qs).qs

    # Schedule (For Against)
    if poll.poll_type == Poll.PollType.SCHEDULE:
        if delegates:
            qs = PollVotingTypeForAgainst.objects.filter(proposal__poll=poll,
                                                         author_delegate__isnull=False).order_by('-vote').all()
        else:
            qs = PollVotingTypeForAgainst.objects.filter(proposal__poll=poll,
                                                         author__created_by=group_user).order_by('-vote').all()

        return BasePollVoteForAgainstFilter(filters, qs).qs


def poll_delegates_list(*, fetched_by: User, group_id: int, poll_id: int, filters=None):
    poll = get_object(Poll, id=poll_id)
    group_user_permissions(group=group_id, user=fetched_by)
    filters = filters or {}
    qs = PollDelegateVoting.objects.filter(poll=poll).all()
    return BasePollDelegateVotingFilter(filters, qs).qs
