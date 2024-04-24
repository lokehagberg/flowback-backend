import random
from celery import shared_task
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import Count, Q, Sum, OuterRef, Case, When, F, Subquery
from django.db.models.functions import Cast
from django.utils import timezone

from flowback.common.services import get_object
from flowback.group.models import GroupTags, GroupUser
from flowback.poll.models import Poll, PollAreaStatement, PollPredictionBet, PollPredictionStatementVote, \
    PollPredictionStatement

import numpy as np


@shared_task
def poll_area_vote_count(poll_id: int):
    poll = get_object(Poll, id=poll_id)
    statement = PollAreaStatement.objects.filter(poll=poll).annotate(
        result=Count('pollareastatementvote', filter=Q(pollareastatementvote__vote=True)) -
               Count('pollareastatementvote', filter=Q(pollareastatementvote__vote=False))).order_by('-result').first()

    if statement:
        tag = GroupTags.objects.filter(pollareastatementsegment__poll_area_statement_id=statement).first()
        poll.tag = tag
        poll.save()

        # Clean all area tag votes, we won't need it anymore
        PollAreaStatement.objects.filter(poll=poll).delete()

    return poll


@shared_task
def poll_prediction_bet_count(poll_id: int):
    # For one prediction, assuming no bias and stationary predictors
    history_limit = 100

    # Get every predictor participating in poll
    timestamp = timezone.now()  # Avoid new bets causing list to be offset
    poll = get_object(Poll, id=poll_id)
    predictors = GroupUser.objects.filter(pollpredictionbet__prediction_statement__poll=poll).all()

    # Get list of previous outcomes in a given area (poll)
    statements = PollPredictionStatement.objects.filter(
        Q(poll__tag=poll.tag,
          poll__end_date__lte=timestamp,
          created_at__lte=timestamp) | Q(poll=poll)
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
    # statement_history = statements.filter(~Q(poll=poll)).all()
    poll_statements = statements.filter(poll=poll).all()

    current_bets = []
    previous_bets = []
    for predictor in predictors:
        # get each bet predictor does, order by previous_outcomes
        bet_subquery = PollPredictionBet.objects.filter(prediction_statement=OuterRef('id'),
                                                        created_by=predictor
                                                        ).annotate(
            real_score=Cast(F('score'), models.FloatField()) / 5).values('real_score')
        bets = statements.annotate(user_bets=Subquery(bet_subquery)).all()

        current_bets.append(list(bets.filter(poll=poll).values_list('user_bets', flat=True)))
        previous_bets.append(list(bets.filter(~Q(poll=poll)).values_list('user_bets', flat=True)))

    #     # TODO get all current_bets for every statement in poll, bets needs to be counted once
    #
    #     predictor_bets.append(bets)

    # Get bets

    # Get list of bets in the given poll, ordered
    #   - if any bet missing, dismiss count

    # Small decimal (AT LEAST a magnitude below 10^(-6))
    small_decimal = 10 ** -7

    # Current bets by each predictor for one given statement, in order
    #   (first equal to predictor 1 bets, 2 to 2 bets etc.)
    # IMPORTANT: do not append the current bet until AFTER the combined bet has been calculated
    #   and saved and there is an outcome
    # current_bets = np.array([[0.99], [0.9]])

    # Create lists of predictor bets in order (matching outcomes, None for missing),
    #   don't include ongoing bets (max 100)
    # If the determinant of a predictor bets list is zero then set the first value to the smallest non zero value
    # TODO future test combinations of values
    # previous_bets = [[0, 1, 0.7, 0, 1], [0, 0.2, 1, 0, 0.8]]
    print(current_bets)
    print(previous_outcomes)
    print(previous_bets)

    bias_adjustments = []  # Assume previous_bets matches order of current_bets

    # If there's no previous bets then do nothing
    if len(previous_bets) == 0 or len(previous_bets[0]) == 0:
        print("No previous bets found, returning", sum(sum(bets) for bets in current_bets) / len(current_bets))
        return 0 if len(current_bets) == 0 else sum(sum(bets) for bets in current_bets) / len(current_bets)

    # Calculation below
    for i, statement in enumerate(poll_statements):
        predictor_errors = []
        for bets in previous_bets:
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

        bet_weights = nominator * (1 / denominator)
        transposed_bet_weights = np.transpose(bet_weights)

        combined_bet = float(np.matmul(transposed_bet_weights,
                                       [bet[i] + bias_adjustments[i] for bet in current_bets])[0])

        # Sanity check
        check = np.matmul(transposed_bet_weights, row_one_vector)
        if (check[0] > 1 + small_decimal) or (0.99 + small_decimal > check[0]):
            print(f"Error with weights: {check[0]:.4f}")

        print(combined_bet)

        statement.combined_bet = combined_bet
        statement.save()
