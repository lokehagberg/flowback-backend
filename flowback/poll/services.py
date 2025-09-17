from django.db.models import Sum, Q, Count, F, OuterRef, Subquery
from rest_framework.exceptions import ValidationError
from flowback.common.services import get_object, model_update
from flowback.group.models import GroupUserDelegatePool
from flowback.poll.models import Poll, PollProposal, PollVoting, PollVotingTypeRanking, PollDelegateVoting, \
    PollVotingTypeForAgainst, PollProposalTypeSchedule
from flowback.group.selectors import group_user_permissions
from django.utils import timezone
from datetime import datetime


def poll_create(*, user_id: int, group_id: int,
                title: str,
                description: str,
                start_date: datetime,
                end_date: datetime,
                poll_type: int,
                public: bool,
                tag: int,
                dynamic: bool
                ) -> Poll:
    group_user = group_user_permissions(user=user_id, group=group_id, permissions=['create_poll', 'admin'])
    poll = Poll(created_by=group_user, title=title, description=description,
                start_date=start_date, end_date=end_date,
                poll_type=poll_type, public=public, tag_id=tag, dynamic=dynamic)
    poll.full_clean()
    poll.save()

    return poll


def poll_update(*, user_id: int, group_id: int, poll_id: int, data) -> Poll:
    group_user = group_user_permissions(user=user_id, group=group_id)
    poll = get_object(Poll, id=poll_id)

    if not poll.created_by == group_user or not group_user.is_admin:
        raise ValidationError('Permission denied')

    non_side_effect_fields = ['title', 'description']

    poll, has_updated = model_update(instance=poll,
                                     fields=non_side_effect_fields,
                                     data=data)

    return poll


def poll_delete(*, user_id: int, group_id: int, poll_id: int) -> None:
    group_user = group_user_permissions(user=user_id, group=group_id)
    poll = get_object(Poll, id=poll_id)

    if not poll.created_by == group_user or not group_user.is_admin:
        raise ValidationError('Permission denied')

    if (poll.created_by == group_user and not group_user.is_admin
    and not group_user.group.created_by == group_user) and poll.start_date < timezone.now():
        raise ValidationError('Only group admins (or above) can delete ongoing polls')

    if poll.finished:
        raise ValidationError('Only site admins (or above) can delete finished polls')

    poll.delete()


def poll_proposal_create(*, user_id: int, group_id: int, poll_id: int, title: str, description: str, data) -> PollProposal:
    group_user = group_user_permissions(user=user_id, group=group_id)
    poll = get_object(Poll, id=poll_id)

    proposal = PollProposal(created_by=group_user, poll=poll, title=title, description=description)

    if poll.type == Poll.PollType.SCHEDULE:
        if not data.get('start_date') and not data.get('end_date'):
            raise Exception('Missing start_date and/or end_date, for proposal schedule creation')

        PollProposalTypeSchedule(proposal=proposal, start_date=data['start_date'], end_date=data['end_date'])

    proposal.full_clean()
    proposal.save()

    return proposal


def poll_proposal_delete(*, user_id: int, group_id: int, poll_id: int, proposal_id: int) -> None:
    group_user = group_user_permissions(user=user_id, group=group_id)
    proposal = get_object(PollProposal, id=proposal_id, poll_id=poll_id)

    if not proposal.created_by == group_user:
        raise ValidationError('Permission denied')

    if proposal.poll.finished:
        raise ValidationError('Only site administrators and above can delete proposals after the poll is finished.')

    proposal.delete()


def poll_proposal_vote_update(*, user_id: int, group_id: int, poll_id: int, data: dict) -> None:
    group_user = group_user_permissions(user=user_id, group=group_id, permissions=['allow_vote', 'admin'])
    poll = get_object(Poll, id=poll_id)

    if poll.poll_type == Poll.PollType.RANKING:
        if not data['votes']:
            PollVoting.objects.filter(created_by=group_user, poll=poll).delete()
            return

        proposals = poll.pollproposal_set.filter(id__in=[x for x in data['votes']]).all()
        if len(proposals) != len(data['votes']):
            raise ValidationError('Not all proposals are available to vote for')

        poll_vote, created = PollVoting.objects.get_or_create(created_by=group_user, poll=poll)
        poll_vote_ranking = [PollVotingTypeRanking(author=poll_vote,
                                                   proposal_id=proposal,
                                                   priority=len(data['votes']) - priority)
                             for priority, proposal in enumerate(data['votes'])]
        PollVotingTypeRanking.objects.filter(author=poll_vote).delete()
        PollVotingTypeRanking.objects.bulk_create(poll_vote_ranking)

    elif poll.poll_type == Poll.PollType.SCHEDULE:
        if not data['votes']:
            PollVoting.objects.filter(created_by=group_user, poll=poll).delete()
            return

        proposals = poll.pollproposal_set.filter(id__in=data['votes']).all()

        if len(proposals) != len(data['votes']):
            raise ValidationError('Not all proposals are available to vote for')

        poll_vote, created = PollVoting.objects.get_or_create(created_by=group_user, poll=poll)
        poll_vote_schedule = [PollVotingTypeForAgainst(author=poll_vote,
                                                       proposal_id=proposal,
                                                       vote=True)
                              for proposal in enumerate(data['votes'])]
        PollVotingTypeForAgainst.objects.filter(author=poll_vote).delete()
        PollVotingTypeForAgainst.objects.bulk_create(poll_vote_schedule)

    else:
        raise ValidationError('Unknown poll type')


# TODO update in future for delegate pool
def poll_proposal_delegate_vote_update(*, user_id: int, group_id: int, poll_id: int, data) -> None:
    group_user = group_user_permissions(user=user_id, group=group_id)
    delegate_pool = get_object(GroupUserDelegatePool, groupuserdelegate__group_user=group_user)
    poll = get_object(Poll, id=poll_id)

    if poll.poll_type == Poll.PollType.RANKING:
        if not data['votes']:
            PollDelegateVoting.objects.filter(created_by=delegate_pool, poll=poll).delete()
            return

        proposals = poll.pollproposal_set.filter(id__in=data['votes']).all()

        if len(proposals) != len(data['votes']):
            raise ValidationError('Not all proposals are available to vote for')

        poll_vote, created = PollDelegateVoting.objects.get_or_create(created_by=delegate_pool, poll=poll)
        poll_vote_ranking = [PollVotingTypeRanking(author_delegate=poll_vote,
                                                   proposal_id=proposal,
                                                   priority=len(data['votes']) - priority)
                             for priority, proposal in enumerate(data['votes'])]
        PollVotingTypeRanking.objects.filter(author_delegate=poll_vote).delete()
        PollVotingTypeRanking.objects.bulk_create(poll_vote_ranking)

    elif poll.poll_type == Poll.PollType.SCHEDULE:
        if not data['votes']:
            PollDelegateVoting.objects.filter(created_by=delegate_pool, poll=poll).delete()
            return

        proposals = poll.pollproposal_set.filter(id__in=data['votes']).all()

        if len(proposals) != len(data['votes']):
            raise ValidationError('Not all proposals are available to vote for')

        poll_vote, created = PollDelegateVoting.objects.get_or_create(created_by=delegate_pool, poll=poll)
        poll_vote_schedule = [PollVotingTypeForAgainst(author_delegate=poll_vote,
                                                       proposal_id=proposal,
                                                       vote=True)
                              for proposal in enumerate(data['votes'])]
        PollVotingTypeForAgainst.objects.filter(author_delegate=poll_vote).delete()
        PollVotingTypeForAgainst.objects.bulk_create(poll_vote_schedule)

    else:
        raise ValidationError('Unknown poll type')


def poll_proposal_vote_count(*, poll_id: int) -> None:
    poll = get_object(Poll, id=poll_id)
    total_proposals = poll.pollproposal_set.count()

    # Count mandate for each delegate, multiply it by score
    mandate = GroupUserDelegatePool.objects.filter(polldelegatevoting__poll=poll).aggregate(
        mandate=Count('groupuserdelegator',
                      filter=~Q(groupuserdelegator__delegator__pollvoting__poll=poll) &
                      Q(groupuserdelegator__tags__in=[poll.tag])))['mandate']

    mandate_subquery = GroupUserDelegatePool.objects.filter(id=OuterRef('author_delegate__created_by')).annotate(
        mandate=Count('groupuserdelegator',
                      filter=~Q(groupuserdelegator__delegator__pollvoting__poll=poll) &
                             Q(groupuserdelegator__tags__in=[poll.tag]))).values('mandate')

    if poll.poll_type == Poll.PollType.RANKING:
        if poll.tag:
            delegate_votes = PollVotingTypeRanking.objects.filter(author_delegate__poll=poll).values('pk').annotate(
                score=(total_proposals - (Count('author_delegate__pollvotingtyperanking') - F('priority'))) *
                Subquery(mandate_subquery))

            # Set score to the same as priority for user votes
            user_votes = PollVotingTypeRanking.objects.filter(author__poll=poll
                                                              ).values('pk').annotate(
                score=total_proposals - (Count('author__pollvotingtyperanking') - F('priority')))

            for i in user_votes:
                PollVotingTypeRanking.objects.filter(id=i['pk']).update(score=i['score'])

            for i in delegate_votes:
                PollVotingTypeRanking.objects.filter(id=i['pk']).update(score=i['score'])

            # TODO make this work, replace both above
            # PollVotingTypeRanking.objects.bulk_update(delegate_votes | user_votes, fields=('score',))

            # Update scores on each proposal, Summarize both regular votes and delegate votes
            proposals = PollProposal.objects.filter(poll_id=poll_id).values('pk') \
                .annotate(score=Sum('pollvotingtyperanking__score'))

            for i in proposals:
                PollProposal.objects.filter(id=i['pk']).update(score=i['score'])

            # TODO make this work aswell, replace above
            # PollProposal.objects.bulk_update(proposals, fields=('score',))

            poll.participants = mandate + PollVoting.objects.filter(poll=poll).all().count()
            poll.save()

    if poll.poll_type == Poll.PollType.SCHEDULE:
        if poll.tag:
            delegate_votes = PollVotingTypeForAgainst.objects.filter(author_delegate__poll=poll).values('pk').annotate(
                score=(Count('author_delegate__pollvotingtypeforagainst',
                             filter=Q(vote=True)) * Subquery(mandate_subquery) -
                       Count('author_delegate__pollvotingtypeforagainst',
                             filter=Q(vote=False)) * Subquery(mandate_subquery)))

            # Set score to the same as priority for user votes
            user_votes = PollVotingTypeRanking.objects.filter(author__poll=poll
                                                              ).values('pk').annotate(
                score=total_proposals - (Count('author__pollvotingtyperanking', filter=Q(vote=True)) -
                                         Count('author__pollvotingtyperanking', filter=Q(vote=False))))

            for i in user_votes:
                PollVotingTypeRanking.objects.filter(id=i['pk']).update(score=i['score'])

            for i in delegate_votes:
                PollVotingTypeRanking.objects.filter(id=i['pk']).update(score=i['score'])

            # TODO make this work, replace both above (Copied from ranking comment)
            # PollVotingTypeSchedule.objects.bulk_update(delegate_votes | user_votes, fields=('score',))

            # Update scores on each proposal, Summarize both regular votes and delegate votes
            proposals = PollProposal.objects.filter(poll_id=poll_id).values('pk') \
                .annotate(score=Sum('pollvotingtypeschedule__score'))

            for i in proposals:
                PollProposal.objects.filter(id=i['pk']).update(score=i['score'])

            # TODO make this work aswell, replace above
            # PollProposal.objects.bulk_update(proposals, fields=('score',))

            poll.participants = mandate + PollVoting.objects.filter(poll=poll).all().count()
            poll.save()


def poll_finish(*, poll_id: int) -> None:
    poll = get_object(Poll, id=poll_id)

    if poll.finished:
        raise ValidationError("Poll is already finished")

    poll_proposal_vote_count(poll_id=poll_id)
    poll.finished = True
    poll.result = True
    poll.save()


def poll_refresh(*, poll_id: int) -> None:
    poll = get_object(Poll, id=poll_id)

    if not poll.dynamic:
        raise ValidationError("Attempted to refresh a poll that doesn't allow live update")

    if poll.finished:
        raise ValidationError("Attempted to refresh a poll that's already finished")

    poll_proposal_vote_count(poll_id=poll_id)


# TODO setup celery
def poll_refresh_cheap(*, poll_id: int) -> None:
    poll = get_object(Poll, id=poll_id)
    if poll.end_date <= timezone.now():
        poll.finished = True
        poll.save()

    if poll.finished and not poll.result or poll.dynamic and not poll.finished:
        poll_proposal_vote_count(poll_id=poll_id)
        poll.refresh_from_db()
        poll.result = True
        poll.save()
