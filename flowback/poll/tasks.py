import random
from celery import shared_task
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import Count, Q, Sum, OuterRef, Case, When, F, Subquery
from django.db.models.functions import Cast
from django.utils import timezone

from flowback.common.services import get_object
from flowback.group.models import GroupTags, GroupUser, GroupUserDelegatePool
from flowback.poll.models import Poll, PollAreaStatement, PollPredictionBet, PollPredictionStatementVote, \
    PollPredictionStatement, PollDelegateVoting, PollVotingTypeRanking, PollProposal, PollVoting, \
    PollVotingTypeCardinal, PollVotingTypeForAgainst

import numpy as np

from flowback.schedule.services import create_event


@shared_task
def poll_area_vote_count(poll_id: int):
    poll = get_object(Poll, id=poll_id)
    statement = PollAreaStatement.objects.filter(poll=poll).annotate(
        result=Count('pollareastatementvote', filter=Q(pollareastatementvote__vote=True)) -
               Count('pollareastatementvote', filter=Q(pollareastatementvote__vote=False))
    ).order_by('-result').first()

    if statement:
        tag = GroupTags.objects.filter(pollareastatementsegment__poll_area_statement=statement).first()
        poll.tag = tag
        poll.save()

        # Clean all area tag votes, we won't need it anymore
        PollAreaStatement.objects.filter(poll=poll).delete()

    return poll


@shared_task
def poll_prediction_bet_count(poll_id: int):
    # For one prediction, assuming no bias and stationary predictors

    # Get every predictor participating in poll
    timestamp = timezone.now()  # Avoid new bets causing list to be offset
    poll = Poll.objects.get(id=poll_id)
    poll.status_prediction = 2
    poll.save()

    # Get list of previous outcomes in a given area (poll)
    statements = PollPredictionStatement.objects.filter(
        Q(Q(poll__tag=poll.tag,
            poll__end_date__lte=timestamp,
            created_at__lte=timestamp) & ~Q(poll=poll)) | Q(poll=poll)
    ).annotate(
        outcome_sum=Sum(Case(When(pollpredictionstatementvote__vote=True, then=1),
                             When(pollpredictionstatementvote__vote=False, then=-1),
                             default=0,
                             output_field=models.IntegerField())),
        outcome=Case(When(outcome_sum__gt=0, then=1),
                     When(outcome_sum__lt=0, then=0),
                     default=0.5,
                     output_field=models.FloatField())
    ).order_by('-created_at').all()

    previous_outcomes = list(statements.filter(~Q(poll=poll)).values_list('outcome', flat=True))
    previous_outcome_avg = 0 if len(previous_outcomes) == 0 else sum(previous_outcomes) / len(previous_outcomes)
    poll_statements = statements.filter(poll=poll).all()

    current_bets = []
    previous_bets = []

    # Get group users associated with the relevant poll
    predictors = GroupUser.objects.filter(pollpredictionbet__prediction_statement__poll=poll).all().distinct()

    for predictor in predictors:
        current_bets.append(list(PollPredictionBet.objects.filter(
            created_by=predictor,
            prediction_statement__in=statements,
            prediction_statement__poll=poll).order_by('-prediction_statement__poll__created_at').annotate(
            real_score=Cast(F('score'), models.FloatField()) / 5).values_list('real_score', flat=True)))

        previous_bets.append(list(PollPredictionBet.objects.filter(
            Q(created_by=predictor,
            prediction_statement__in=statements)
            & ~Q(prediction_statement__poll=poll)).order_by('-prediction_statement__poll__created_at').annotate(
            real_score=Cast(F('score'), models.FloatField()) / 5).values_list('real_score', flat=True)))

    # Get bets

    # Get list of bets in the given poll, ordered
    #   - if any bet missing, dismiss count

    # Small decimal (AT LEAST a magnitude below 10^(-6))
    small_decimal = 10 ** -7

    # Current bets by each predictor for one given statement, in order # TODO Loke check this
    #   (first equal to predictor 1 bets, 2 to 2 bets etc.)
    # IMPORTANT: do not append the current bet until AFTER the combined bet has been calculated
    #   and saved and there is an outcome
    # current_bets = np.array([[0.99], [0.9]])

    # Create lists of predictor bets in order (matching outcomes, None for missing),
    #   don't include ongoing bets (max 100)
    # If the determinant of a predictor bets list is zero then set the first value to the smallest non zero value
    # TODO future test combinations of values
    # previous_bets = [[0, 1, 0.7, 0, 1], [0, 0.2, 1, 0, 0.8]]
    print("\n\n" + "#" * 50)

    # Assume previous_bets matches order of current_bets
    print("Current Bets:", current_bets)
    print("Previous Outcomes:", previous_outcomes)
    print("Previous Bets:", previous_bets)

    # Calculation below
    for i, statement in enumerate(poll_statements):
        bias_adjustments = []
        predictor_errors = []
        main_bets = [bets[i] for bets in current_bets if bets[i] is not None]

        # If there's no previous bets then do nothing
        if len(previous_bets) == 0 or len(previous_bets[0]) == 0:
            result = None if all(bets[i] is not None for bets in current_bets) else (sum(main_bets)) / len(main_bets)
            print(f"No previous bets found, returning {result}")
            statement.combined_bet = result
            statement.save()

            continue

        # Skip if all current bets for a given prediction statement is equal to None
        if all(x[i] is None for x in current_bets):
            continue

        previous_bets_trimmed = [previous_bets[j] for j in range(len(previous_bets)) if current_bets[j][i] is not None]
        print("Previous Bets Trimmed:", previous_bets_trimmed)
        for bets in previous_bets_trimmed:
            bets_trimmed = [i for i in bets if i is not None]
            bias_adjustments.append(0 if len(bets) == 0 else previous_outcome_avg - (sum(bets_trimmed) /
                                                                                     len(bets_trimmed)))

            predictor_errors.append(np.array([previous_outcomes[i] - bets[i]
                                              if bets[i] is not None
                                              else None for i in range(len(previous_outcomes))]))

        # If a predictor has not bet on a certain prediction then their bet will be None for said prediction
        def drop_incomparable_values(arr_1, arr_2):
            drop_list = []

            for i in range(len(arr_1)):
                if arr_1[i] is None or arr_2[i] is None:
                    drop_list.append(i)

            arr_1 = np.delete(arr_1, drop_list)
            arr_2 = np.delete(arr_2, drop_list)

            return arr_1, arr_2

        def covariance(arr_1, arr_2):
            covariance_array = [(arr_1[i] - np.mean(arr_1)) * (arr_2[i] - np.mean(arr_2)) for i in range(len(arr_1))]
            return (1 / len(arr_1)) * sum(covariance_array)

        covariance_matrix = []
        for k in range(len(predictor_errors)):
            row = []

            for j in range(len(predictor_errors)):
                comparable_errors = drop_incomparable_values(predictor_errors[k], predictor_errors[j])
                row.append(covariance(comparable_errors[0], comparable_errors[1]))

            covariance_matrix.append(row)

        # TODO check the following if statement is valid
        if not covariance_matrix:
            continue

        np_covariance_matrix = np.array(covariance_matrix)

        # The inverse only exists when the determinant is non-zero, this can be made sure of by changing small decimals
        if np.linalg.det(np_covariance_matrix) == 0:
            determinant_is_zero = True
            print("Zero determinant")

            while determinant_is_zero:
                for m in range(np_covariance_matrix.shape[0]):
                    for j in range(np_covariance_matrix.shape[0]):
                        np_covariance_matrix[m][j] += small_decimal * [-1, 1][random.randint(0, 1)]

                det = np.linalg.det(np_covariance_matrix)
                if det != 0:
                    determinant_is_zero = False

        inverse_covariance_matrix = np.linalg.inv(np_covariance_matrix)

        column_one_vector = np.array([[1]] * inverse_covariance_matrix.shape[0])
        row_one_vector = np.array([1] * inverse_covariance_matrix.shape[0])

        nominator = np.matmul(inverse_covariance_matrix, column_one_vector)

        denominator_vector = np.matmul(inverse_covariance_matrix, row_one_vector)
        denominator = np.matmul(row_one_vector, denominator_vector)

        if denominator == 0:
            denominator = small_decimal

        bet_weights = nominator * (1 / denominator)
        transposed_bet_weights = np.transpose(bet_weights)

        print("Transposed_bet_weights:", transposed_bet_weights)
        print("Main bets:", main_bets)
        print("Bias_adjustments:", bias_adjustments)

        # I am unsure if I should limit the bias adjusted bets or only limit the combined bet in the end,
        # I think this might make more sense but I have to think about this more
        # TODO: think about this more
        bias_adjusted_bet = [bet + bias_adjustments[i] for bet in main_bets]
        for j in range(len(bias_adjusted_bet)):
            if bias_adjusted_bet[j] < 0:
                bias_adjusted_bet[j] = 0.0
            elif bias_adjusted_bet[j] > 1:
                bias_adjusted_bet[j] = 1.0

        combined_bet = float(np.matmul(transposed_bet_weights, bias_adjusted_bet)[0])

        if combined_bet < 0:
            combined_bet = 0
        elif combined_bet > 1:
            combined_bet = 1

        # Sanity check
        check = np.matmul(transposed_bet_weights, row_one_vector)
        if (check[0] > 1 + small_decimal) or (0.99 + small_decimal > check[0]):
            print(f"Error with weights: {check[0]:.4f}")

        print(combined_bet)

        statement.combined_bet = combined_bet
        statement.save()

    poll.status_prediction = 1
    poll.save()


@shared_task
def poll_proposal_vote_count(poll_id: int) -> None:
    poll = get_object(Poll, id=poll_id)
    group = poll.created_by.group
    total_proposals = poll.pollproposal_set.count()

    if poll.status:
        return

    # Count mandate for each delegate, multiply it by score
    # TODO Redundant
    mandate = GroupUserDelegatePool.objects.filter(polldelegatevoting__poll=poll).aggregate(
        mandate=Count('groupuserdelegator',
                      filter=~Q(groupuserdelegator__delegator__pollvoting__poll=poll
                                ) & Q(groupuserdelegator__tags__in=[poll.tag]
                                      ) & Q(groupuserdelegator__delegator__active=True)
                      ))['mandate']

    mandate_subquery = GroupUserDelegatePool.objects.filter(id=OuterRef('author_delegate__created_by')).annotate(
        mandate=Count('groupuserdelegator',
                      filter=~Q(groupuserdelegator__delegator__pollvoting__poll=poll
                                ) & Q(groupuserdelegator__tags__in=[poll.tag]
                                      ) & Q(groupuserdelegator__delegator__active=True)
                      )).values('mandate')

    # Count mandate for each delegate, save it to PollDelegateVoting account
    total_mandate = PollDelegateVoting.objects.filter(id=OuterRef('id')).annotate(
        total_mandate=Count('created_by__groupuserdelegator',
                      filter=~Q(created_by__groupuserdelegator__delegator__pollvoting__poll=poll
                                ) & Q(created_by__groupuserdelegator__tags__in=[poll.tag]
                                      ) & Q(created_by__groupuserdelegator__delegator__active=True)
                      )).values('total_mandate')

    PollDelegateVoting.objects.update(mandate=Subquery(total_mandate))

    if poll.poll_type == Poll.PollType.RANKING:
        if poll.tag:
            delegate_votes = PollVotingTypeRanking.objects.filter(author_delegate__poll=poll).values('pk').annotate(
                score=(total_proposals - (Count('author_delegate__pollvotingtyperanking') - F('priority'))
                       ) * Subquery(mandate_subquery))

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

    if poll.poll_type == Poll.PollType.CARDINAL:
        if poll.tag:
            # Calculate user scores
            # user_weight = PollVoting.objects.filter(id=OuterRef('author'), poll=poll
            #                                         ).annotate(weight=Sum('pollvotingtypecardinal__raw_score')
            #                                                    ).values('weight')
            PollVotingTypeCardinal.objects.filter(author__isnull=False,
                                                  proposal__poll=poll).update(score=F('raw_score'))
            # delegate_weight = PollDelegateVoting.objects.filter(id=OuterRef('author_delegate'), poll=poll
            #                                                 ).annotate(weight=Sum('pollvotingtypecardinal__raw_score')
            #                                                            ).values('weight')
            # Calculate delegate scores
            delegate_scores = PollVotingTypeCardinal.objects.filter(id=OuterRef('id')).annotate(
                final_score=F('raw_score') * F('author_delegate__mandate')).values('final_score')
            PollVotingTypeCardinal.objects.filter(author_delegate__isnull=False, proposal__poll=poll
                                                  ).update(score=Subquery(delegate_scores))

            proposal_scores = PollProposal.objects.filter(id=OuterRef('id')).annotate(final_score=Sum('pollvotingtypecardinal__score')).values('final_score')
            PollProposal.objects.update(score=Subquery(proposal_scores))

    if poll.poll_type == Poll.PollType.SCHEDULE:
        if poll.tag:
            delegate_votes = PollVotingTypeForAgainst.objects.filter(author_delegate__poll=poll).values('pk').annotate(
                score=(Count('author_delegate__pollvotingtypeforagainst',
                             filter=Q(vote=True)) * Subquery(mandate_subquery) -
                       Count('author_delegate__pollvotingtypeforagainst',
                             filter=Q(vote=False)) * Subquery(mandate_subquery)))

            # Set score to the same as priority for user votes
            user_votes = PollVotingTypeForAgainst.objects.filter(author__poll=poll, vote=True).values('pk', 'vote')

            for i in user_votes:
                PollVotingTypeForAgainst.objects.filter(id=i['pk']).update(score=int(i['vote']))

            for i in delegate_votes:
                PollVotingTypeForAgainst.objects.filter(id=i['pk']).update(score=int(i['vote']))

            # TODO make this work, replace both above (Copied from ranking comment)
            # PollVotingTypeSchedule.objects.bulk_update(delegate_votes | user_votes, fields=('score',))

            # Update scores on each proposal, Summarize both regular votes and delegate votes
            proposals = PollProposal.objects.filter(poll_id=poll_id).values('pk') \
                .annotate(score=Sum('pollvotingtypeforagainst__score'))

            for i in proposals:
                PollProposal.objects.filter(id=i['pk']).update(score=i['score'])

            # TODO make this work aswell, replace above
            # PollProposal.objects.bulk_update(proposals, fields=('score',))

            poll.participants = (mandate + PollVoting.objects.filter(poll=poll).all().count()) or 1

    total_group_users = GroupUser.objects.filter(group=group).count()
    quorum = (poll.quorum if poll.quorum is not None else group.default_quorum) / 100

    if poll.finished and not poll.result:
        if poll.poll_type == Poll.PollType.SCHEDULE:
            winning_proposal = PollProposal.objects.filter(
                poll_id=poll_id).order_by('-score', '-pollproposaltypeschedule__event__start_date').first()
            if winning_proposal:
                event = winning_proposal.pollproposaltypeschedule.event
                create_event(schedule_id=group.schedule_id,
                             title=poll.title,
                             start_date=event.start_date,
                             end_date=event.end_date,
                             origin_name=poll.schedule_origin,
                             origin_id=poll.id,
                             description=poll.description)

        poll.status = 1 if poll.participants > total_group_users * quorum else -1
        poll.result = True
        poll.save()
