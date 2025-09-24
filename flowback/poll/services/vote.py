from rest_framework.exceptions import ValidationError

from backend.settings import FLOWBACK_SCORE_VOTE_CEILING, FLOWBACK_SCORE_VOTE_FLOOR
from flowback.common.services import get_object
from flowback.group.models import GroupUserDelegatePool
from flowback.group.notify import notify_group_user_delegate_pool_poll_vote_update
from flowback.notification.models import NotificationChannel
from flowback.poll.models import Poll, PollVoting, PollVotingTypeRanking, PollDelegateVoting, \
    PollVotingTypeForAgainst, PollVotingTypeCardinal
from flowback.group.selectors.permission import group_user_permissions


def poll_proposal_vote_update(*, user_id: int, poll_id: int, data: dict) -> None:
    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(user=user_id,
                                        group=poll.created_by.group.id,
                                        permissions=['allow_vote', 'admin'])

    poll.check_phase('delegate_vote', 'vote', 'dynamic', 'schedule')

    if poll.poll_type == Poll.PollType.RANKING:
        if not data['proposals']:
            PollVoting.objects.filter(created_by=group_user, poll=poll).delete()
            return

        proposals = poll.pollproposal_set.filter(id__in=[x for x in data['proposals']]).all()

        if len(proposals) != len(data['proposals']):
            raise ValidationError('Not all proposals are available to vote for')

        poll_vote, created = PollVoting.objects.get_or_create(created_by=group_user, poll=poll)
        poll_vote_ranking = [PollVotingTypeRanking(author=poll_vote,
                                                   proposal_id=proposal,
                                                   priority=len(data['proposals']) - priority)
                             for priority, proposal in enumerate(data['proposals'])]
        PollVotingTypeRanking.objects.filter(author=poll_vote).delete()
        PollVotingTypeRanking.objects.bulk_create(poll_vote_ranking)

    elif poll.poll_type == Poll.PollType.CARDINAL:

        if FLOWBACK_SCORE_VOTE_CEILING is not None and any(
                [score > FLOWBACK_SCORE_VOTE_CEILING for score in data['scores']]):
            raise ValidationError(
                f'Voting scores exceeds ceiling bounds (currently set at {FLOWBACK_SCORE_VOTE_CEILING})')

        if FLOWBACK_SCORE_VOTE_FLOOR is not None and any(
                [score < FLOWBACK_SCORE_VOTE_FLOOR for score in data['scores']]):
            raise ValidationError(f'Voting scores exceeds floor bounds (currently set at {FLOWBACK_SCORE_VOTE_FLOOR})')

        # Delete votes if no polls are registered
        if not data['proposals']:
            PollVoting.objects.filter(created_by=group_user, poll=poll).delete()
            return

        if len(data['scores']) != len(data['proposals']):
            raise ValidationError("The amount of votes don't match the amount of polls")

        proposals = poll.pollproposal_set.filter(id__in=data['proposals']).all()
        if len(proposals) != len(data['proposals']):
            raise ValidationError('Not all proposals are available to vote for')

        user_vote, created = PollVoting.objects.get_or_create(created_by=group_user, poll=poll)
        poll_vote_cardinal = [PollVotingTypeCardinal(author=user_vote,
                                                     proposal_id=data['proposals'][i],
                                                     raw_score=data['scores'][i])
                              for i in range(len(data['proposals']))]

        PollVotingTypeCardinal.objects.filter(author=user_vote).delete()
        PollVotingTypeCardinal.objects.bulk_create(poll_vote_cardinal)

    elif poll.poll_type == Poll.PollType.SCHEDULE:
        if not data['proposals']:
            PollVoting.objects.filter(created_by=group_user, poll=poll).delete()
            return

        proposals = poll.pollproposal_set.filter(id__in=data['proposals']).all()

        if len(proposals) != len(data['proposals']):
            raise ValidationError('Not all proposals are available to vote for')

        poll_vote, created = PollVoting.objects.get_or_create(created_by=group_user, poll=poll)
        poll_vote_schedule = [PollVotingTypeForAgainst(author=poll_vote,
                                                       proposal_id=proposal,
                                                       vote=True)
                              for proposal in data['proposals']]
        PollVotingTypeForAgainst.objects.filter(author=poll_vote).delete()
        PollVotingTypeForAgainst.objects.bulk_create(poll_vote_schedule)

    else:
        raise ValidationError('Unknown poll type')


# TODO update in future for delegate pool
def poll_proposal_delegate_vote_update(*, user_id: int, poll_id: int, data) -> None:
    poll = Poll.objects.get(id=poll_id)
    group_user = group_user_permissions(user=user_id, group=poll.created_by.group.id)

    try:
        delegate_pool = GroupUserDelegatePool.objects.get(groupuserdelegate__group_user=group_user)

    except GroupUserDelegatePool.DoesNotExist:
        raise ValidationError("User is not a delegate")

    if group_user.group.id != poll.created_by.group.id:
        raise ValidationError('Permission denied')

    poll.check_phase('delegate_vote', 'dynamic', 'schedule')

    if poll.poll_type == Poll.PollType.RANKING:
        if not data['proposals']:
            PollDelegateVoting.objects.filter(created_by=delegate_pool, poll=poll).delete()
            return

        proposals = poll.pollproposal_set.filter(id__in=data['proposals']).all()

        if len(proposals) != len(data['proposals']):
            raise ValidationError('Not all proposals are available to vote for')

        poll_vote, created = PollDelegateVoting.objects.get_or_create(created_by=delegate_pool, poll=poll)
        poll_vote_ranking = [PollVotingTypeRanking(author_delegate=poll_vote,
                                                   proposal_id=proposal,
                                                   priority=len(data['proposals']) - priority)
                             for priority, proposal in enumerate(data['proposals'])]
        PollVotingTypeRanking.objects.filter(author_delegate=poll_vote).delete()
        PollVotingTypeRanking.objects.bulk_create(poll_vote_ranking)

    elif poll.poll_type == Poll.PollType.CARDINAL:

        # Delete votes if no polls are registered
        if not data['proposals']:
            PollDelegateVoting.objects.filter(created_by=delegate_pool, poll=poll).delete()
            return

        if len(data['scores']) != len(data['proposals']):
            raise ValidationError("The amount of votes don't match the amount of polls")

        proposals = poll.pollproposal_set.filter(id__in=data['proposals']).all()
        if len(proposals) != len(data['proposals']):
            raise ValidationError('Not all proposals are available to vote for')

        if FLOWBACK_SCORE_VOTE_CEILING is not None and any(
                [score > FLOWBACK_SCORE_VOTE_CEILING for score in data['scores']]):
            raise ValidationError(
                f'Voting scores exceeds ceiling bounds (currently set at {FLOWBACK_SCORE_VOTE_CEILING})')

        if FLOWBACK_SCORE_VOTE_FLOOR is not None and any(
                [score < FLOWBACK_SCORE_VOTE_FLOOR for score in data['scores']]):
            raise ValidationError(f'Voting scores exceeds floor bounds (currently set at {FLOWBACK_SCORE_VOTE_FLOOR})')

        pool_vote, created = PollDelegateVoting.objects.get_or_create(created_by=delegate_pool, poll=poll)
        poll_vote_cardinal = [PollVotingTypeCardinal(author_delegate=pool_vote,
                                                     proposal_id=data['proposals'][i],
                                                     raw_score=data['scores'][i])
                              for i in range(len(data['proposals']))]

        PollVotingTypeCardinal.objects.filter(author_delegate=pool_vote).delete()
        PollVotingTypeCardinal.objects.bulk_create(poll_vote_cardinal)

    elif poll.poll_type == Poll.PollType.SCHEDULE:
        if not data['proposals']:
            PollDelegateVoting.objects.filter(created_by=delegate_pool, poll=poll).delete()
            return

        proposals = poll.pollproposal_set.filter(id__in=data['proposals']).all()

        if len(proposals) != len(data['proposals']):
            raise ValidationError('Not all proposals are available to vote for')

        poll_vote, created = PollDelegateVoting.objects.get_or_create(created_by=delegate_pool, poll=poll)
        poll_vote_schedule = [PollVotingTypeForAgainst(author_delegate=poll_vote,
                                                       proposal_id=proposal,
                                                       vote=True)
                              for proposal in enumerate(data['proposals'])]
        PollVotingTypeForAgainst.objects.filter(author_delegate=poll_vote).delete()
        PollVotingTypeForAgainst.objects.bulk_create(poll_vote_schedule)

    else:
        raise ValidationError('Unknown poll type')

    notify_group_user_delegate_pool_poll_vote_update(action=NotificationChannel.Action.UPDATED,
                                                     message="A Delegate you subscribed to has "
                                                             "added/updated their vote(s) on a poll",
                                                     poll=poll,
                                                     delegate_pool=delegate_pool)
