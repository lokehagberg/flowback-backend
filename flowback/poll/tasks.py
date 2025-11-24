import random
from celery import shared_task
from django.db import models
from django.db.models import Count, Q, Sum, OuterRef, Case, When, F, Subquery
from django.db.models.functions import Cast
from django.utils import timezone

from backend.settings import DEBUG
from flowback.common.services import get_object
from flowback.group.models import GroupTags, GroupUser, GroupUserDelegatePool
from flowback.group.selectors.permission import permission_q
from flowback.group.selectors.tags import group_tags_list
from flowback.notification.models import NotificationChannel
from flowback.poll.models import Poll, PollAreaStatement, PollPredictionBet, PollPredictionStatement, \
    PollDelegateVoting, PollVotingTypeRanking, PollProposal, PollVoting, \
    PollVotingTypeCardinal, PollVotingTypeForAgainst

import numpy as np

from flowback.poll.notify import notify_poll


@shared_task
def poll_area_vote_count(poll_id: int):
    tag = None
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

    notify_poll(message="Poll area phase has ended and results have been counted",
                action=NotificationChannel.Action.UPDATED,
                poll=poll)

    return (f"Poll {poll_id} area task completed. "
            f"{'No tags have won.' if not tag else
            f'Tag: {tag.name} has won with {statement.pollareastatementvote_set.all().count()} points.'}")


@shared_task
def poll_prediction_bet_count(poll_id: int):
    # For one prediction, assuming no bias and stationary predictors

    def dprint(*args, **kwargs):
        if DEBUG:
            print(*args, **kwargs)

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
        outcome_scores=Case(When(outcome_sum__gt=0, then=1),
                            When(outcome_sum__lt=0, then=0),
                            default=None,
                            output_field=models.FloatField(null=True))
    ).order_by('-created_at').all()

    previous_outcomes = list(statements.filter(~Q(poll=poll) & Q(outcome_scores__isnull=False)
                                               ).values_list('outcome_scores', flat=True))
    previous_outcome_avg = 0 if len(previous_outcomes) == 0 else sum(previous_outcomes) / len(previous_outcomes)
    poll_statements = statements.filter(poll=poll).all().values_list('id', flat=True)

    # Get group users associated with the relevant poll
    predictors = GroupUser.objects.filter(pollpredictionbet__prediction_statement__poll=poll).all().distinct()

    current_bets = []
    previous_bets = []
    for predictor in predictors:
        # TODO check if statements include the current poll's statements
        bets = list(PollPredictionBet.objects.filter(
            created_by=predictor,
            prediction_statement__in=statements,
            prediction_statement__poll=poll).order_by('-prediction_statement__created_at').annotate(
            real_score=Cast(F('score'), models.FloatField()) / 5).values_list('prediction_statement_id', 'real_score'))

        bets_statements = [i[0] for i in bets]
        current_bet = []
        for statement in poll_statements:
            if statement in bets_statements:
                current_bet.append(bets[bets_statements.index(statement)][1])

            else:
                current_bet.append(None)

        current_bets.append(current_bet)

        unprocessed_previous_bets = PollPredictionBet.objects.filter(
            Q(created_by=predictor, prediction_statement__in=statements.filter(outcome_scores__isnull=False))
            & ~Q(prediction_statement__poll=poll)).order_by('-prediction_statement__created_at').annotate(
            real_score=Cast(F('score'), models.FloatField()) / 5)

        bets = []
        for statement in statements.filter(~Q(poll=poll) & Q(outcome_scores__isnull=False)):
            try:
                bets.append(unprocessed_previous_bets.get(prediction_statement=statement).real_score)

            except PollPredictionBet.DoesNotExist:
                bets.append(None)

        previous_bets.append(bets)

    # Current
    # Bets: [[0.2, 0.2], [0.0, 0.0], [1.0, 0.0]]
    # Previous
    # Outcomes: [1.0]
    # Previous
    # Bets: [[0.0], [0.2], [1.0]]

    # previous_bets = [[] for _ in range(len(predictors))]
    # for i, statement in enumerate(statements.filter(~Q(poll=poll) & Q(outcome_scores__isnull=False))):  # For each previous statement (fix? weed out outcome_scores=None)
    #     for j, predictor in enumerate(predictors):  # For each predictor
    #
    #         # Could be optimized
    #         try:
    #             bet = PollPredictionBet.objects.get(Q(created_by=predictor)
    #                                                 & Q(prediction_statement=statement))  # Get bets from predictor for each statement
    #             previous_bets[j].append(bet.score / 5)  # Divide all bets by 5
    #
    #         except PollPredictionBet.DoesNotExist:
    #             previous_bets[j].append(None)  # If the bet does not exist, add None as a placeholder

    # prediction_bets.append()
    # print(PollPredictionBet.objects.filter(
    #     Q(created_by=predictor,
    #     prediction_statement__in=statements)
    #     & ~Q(prediction_statement__poll=poll)).count())
    #
    # previous_bets.append(list(PollPredictionBet.objects.filter(
    #     Q(created_by=predictor,
    #     prediction_statement__in=statements)
    #     & ~Q(prediction_statement__poll=poll)).order_by('-prediction_statement__poll__created_at').annotate(
    #     real_score=Cast(F('score'), models.FloatField()) / 5).values_list('real_score', flat=True)))

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

    # Delete any predictors with no previous history, if there is at least one user with a previous history
    to_delete = []
    if not all([all(i is None for i in predictor_bets) for predictor_bets in previous_bets]):
        for j, predictor_bets in enumerate(previous_bets):
            if all(i is None for i in predictor_bets):
                to_delete.append(j)

        current_bets = [u for i, u in enumerate(current_bets) if i not in to_delete]
        previous_bets = [u for i, u in enumerate(previous_bets) if i not in to_delete]

    # Delete any previous_outcomes where all corresponding previous bets are None
    to_delete = []
    for j, previous_outcome in enumerate(previous_outcomes):
        if all(bets[j] is None for bets in previous_bets):
            to_delete.append(j)

    previous_outcomes = [j for n, j in enumerate(previous_outcomes) if n not in to_delete]

    for i in range(len(previous_bets)):
        previous_bets[i] = [j for n, j in enumerate(previous_bets[i]) if n not in to_delete]

    dprint("\n\n" + "#" * 50)

    # Assume previous_bets matches order of current_bets
    dprint("Previous Statements count: ", statements.filter(~Q(poll=poll)).count())
    dprint("Current statements count: ", statements.filter(poll=poll).count())
    dprint("Total predictor count: ", predictors.count())
    dprint("Current Bets:", current_bets)
    dprint("Previous Outcomes:", previous_outcomes)
    dprint("Previous Bets:", previous_bets)

    dprint("Total Statement:", len(poll_statements))

    # Calculation below
    # for i, statement in enumerate(poll_statements):
    for i, statement in enumerate(poll_statements):
        bias_adjustments = []
        predictor_errors = []
        main_bets = [bets[i] for bets in current_bets if bets[i] is not None]

        # If there's no previous bets then do nothing
        if len(previous_bets) == 0 or len(previous_bets[0]) == 0:
            combined_bet = None if all(bets[i] is None for bets in current_bets) else (sum(main_bets)) / len(main_bets)
            dprint(f"No previous bets found, returning {combined_bet}")
            PollPredictionStatement.objects.filter(id=statement).update(combined_bet=combined_bet)

            continue

        # Skip if all current bets for a given prediction statement is equal to None
        if all(x[i] is None for x in current_bets):
            continue

        previous_bets_trimmed = [previous_bets[j] for j in range(len(previous_bets)) if current_bets[j][i] is not None]
        dprint("Previous Bets Trimmed:", previous_bets_trimmed)
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
            dprint("Zero determinant")

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

        dprint("Transposed_bet_weights:", transposed_bet_weights)
        dprint("Main bets:", main_bets)
        dprint("Bias_adjustments:", bias_adjustments)

        # I am unsure if I should limit the bias adjusted bets or only limit the combined bet in the end,
        # I think this might make more sense but I have to think about this more
        # TODO: think about this more

        # For main bets is list of bets per predictor
        # Bias adjustments is adjustments per predictor
        #
        bias_adjusted_bet = [main_bets[j] + bias_adjustments[j] for j in range(len(main_bets))]
        for j in range(len(bias_adjusted_bet)):
            if bias_adjusted_bet[j] < 0:
                bias_adjusted_bet[j] = 0.0
            elif bias_adjusted_bet[j] > 1:
                bias_adjusted_bet[j] = 1.0

        dprint(f"Results: {np.matmul(transposed_bet_weights, bias_adjusted_bet)}")
        combined_bet = float(np.matmul(transposed_bet_weights, bias_adjusted_bet)[0])

        if combined_bet < 0:
            combined_bet = 0
        elif combined_bet > 1:
            combined_bet = 1

        # Sanity check
        check = np.matmul(transposed_bet_weights, row_one_vector)
        if (check[0] > 1 + small_decimal) or (0.99 + small_decimal > check[0]):
            dprint(f"Error with weights: {check[0]:.4f}")

        dprint(combined_bet)

        PollPredictionStatement.objects.filter(id=statement).update(combined_bet=combined_bet)

    poll.status_prediction = 1
    poll.save()

    notify_poll(message="Poll prediction phase has ended and results have been counted",
                action=NotificationChannel.Action.UPDATED,
                poll=poll)


@shared_task
def poll_proposal_vote_count(poll_id: int) -> None:
    # Count Mandate
    # Skip ranking and work on cardinal, rename to Poll Score
    # Count user votes
    # Update scores for each vote (keep raw_score intact)
    # Update proposal scores
    # Update participants
    # Check quorum
    # Update poll status
    # Update IMAC
    # Set result to True
    # Save and notify

    poll = Poll.objects.get(id=poll_id)
    group = poll.created_by.group

    # Update the delegate's mandate.
    # Mandate is set to 0 by default
    mandate = GroupUserDelegatePool.objects.filter(id=OuterRef('created_by')).annotate(
        mandate=Count('groupuserdelegator',
                      filter=~Q(groupuserdelegator__delegator__pollvoting__poll=poll)
                             & Q(groupuserdelegator__tags__in=[poll.tag])
                             & Q(groupuserdelegator__delegator__active=True)
                             & permission_q('groupuserdelegator__delegator', 'allow_vote')
                      )).values('mandate')

    PollDelegateVoting.objects.filter(
        permission_q('created_by__groupuserdelegate__group_user', 'allow_vote'),
        poll=poll).update(mandate=Subquery(mandate))

    # Query to get a delegate's mandate
    delegate_mandate = PollDelegateVoting.objects.filter(
        id=OuterRef('author_delegate')
    ).values('mandate')

    if poll.status or poll.poll_type == Poll.PollType.RANKING:
        return

    if poll.poll_type == Poll.PollType.CARDINAL:
        # Update user vote scores
        PollVotingTypeCardinal.objects.filter(
            permission_q('author__created_by', 'allow_vote'),
            author__poll=poll).update(score=F('raw_score'))

        # Update delegate vote scores
        PollVotingTypeCardinal.objects.filter(author_delegate__poll=poll
                                              ).update(score=F('raw_score') * Subquery(delegate_mandate))

        # Update proposal scores
        proposal_scores = PollVotingTypeCardinal.objects.filter(
            proposal=OuterRef('id')
        ).values('proposal').annotate(
            total_score=Sum('score')
        ).values('total_score')

        PollProposal.objects.filter(poll=poll).update(score=Subquery(proposal_scores))

    if poll.poll_type == Poll.PollType.SCHEDULE:
        # Update user vote scores
        PollVotingTypeForAgainst.objects.filter(
            permission_q('author__created_by', 'allow_vote'),
            author__poll=poll).update(score=Case(When(vote=True, then=1), default=-1))

        # Update delegate vote scores
        PollVotingTypeForAgainst.objects.filter(author_delegate__poll=poll
                                                ).update(score=Case(When(vote=True, then=1), default=-1)
                                                               * Subquery(delegate_mandate))

        # Update proposal scores
        proposal_scores = PollVotingTypeForAgainst.objects.filter(
            proposal=OuterRef('id')
        ).values('proposal').annotate(
            total_score=Sum('score')
        ).values('total_score')

        PollProposal.objects.filter(poll=poll).update(score=Subquery(proposal_scores))

    # Check if quorum is fulfilled
    total_group_users = GroupUser.objects.filter(group=group).count()
    quorum = (poll.quorum if poll.quorum is not None else group.default_quorum) / 100
    user_participants = PollVoting.objects.filter(permission_q('created_by', 'allow_vote'),
                                                  poll=poll).count()
    delegate_participants = PollDelegateVoting.objects.filter(poll=poll).aggregate(mandate=Sum('mandate'))['mandate']
    participants = ((user_participants if user_participants is not None else 0)
                    + (delegate_participants if delegate_participants is not None else 0))
    poll.participants = participants
    poll.save()

    if poll.finished and not poll.result:
        print(f"Total Participants: {participants}")
        print(f"Total Group Users: {total_group_users}")
        print(f"Quorum: {quorum}")
        poll.status = 1 if poll.participants >= total_group_users * quorum else -1
        poll.interval_mean_absolute_correctness = group_tags_list(group_id=poll.created_by.group_id,
                                                                  filters=dict(id=poll.tag_id)).first().imac
        poll.result = True
        poll.save()

        notify_poll(message="Poll has ended and results have been counted",
                    action=NotificationChannel.Action.UPDATED,
                    poll=poll)

        if poll.poll_type == Poll.PollType.SCHEDULE and poll.status == 1:
            winning_proposal = PollProposal.objects.filter(
                poll_id=poll_id).order_by('-score', '-pollproposaltypeschedule__event_start_date').first()
            if winning_proposal:
                schedule = group.schedule if poll.work_group is None else poll.work_group.schedule
                schedule.create_event(title=poll.title,
                                      description=poll.description,
                                      meeting_link=poll.schedule_poll_meeting_link,
                                      start_date=winning_proposal.pollproposaltypeschedule.event_start_date,
                                      end_date=winning_proposal.pollproposaltypeschedule.event_end_date,
                                      created_by=poll)
