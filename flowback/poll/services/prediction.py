from typing import Union

from django.db import models
from django.db.models import Sum, Case, When, F, OuterRef, Subquery, Count
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ..models import (PollPredictionBet,
                      PollPredictionStatement,
                      PollPredictionStatementSegment,
                      PollPredictionStatementVote,
                      Poll, PollProposal)
from ...common.services import get_object, model_update
from ...group.selectors.permission import group_user_permissions
from ...user.models import User


def poll_prediction_statement_create(poll: int,
                                     user: Union[int, User],
                                     title: str,
                                     end_date: timezone.datetime,
                                     segments: list[dict],
                                     description: str = None,
                                     attachments: list = None,
                                     blockchain_id: int = None) -> int:
    poll = get_object(Poll, id=poll)
    group_user = group_user_permissions(user=user, group=poll.created_by.group,
                                        permissions=['prediction_statement_create', 'admin'])
    prediction_statement = PollPredictionStatement(created_by=group_user,
                                                   poll=poll,
                                                   title=title,
                                                   description=description,
                                                   attachments=attachments,
                                                   end_date=end_date,
                                                   blockchain_id=blockchain_id)

    valid_proposals = PollProposal.objects.filter(id__in=[i.get('proposal_id') for i in segments],
                                                  poll=poll).all()
    prediction_statement.full_clean()

    poll.check_phase('prediction_statement', 'dynamic')

    if len(segments) < 1:
        raise ValidationError('Prediction statement must contain atleast one statement')

    elif len(valid_proposals) == len(segments):
        prediction_statement_segment = [PollPredictionStatementSegment(proposal_id=segment['proposal_id'],
                                                                       is_true=segment['is_true'],
                                                                       prediction_statement=prediction_statement)
                                        for segment in segments]

        prediction_statement.save()
        PollPredictionStatementSegment.objects.bulk_create(prediction_statement_segment)
        return prediction_statement.id

    else:
        raise ValidationError('Prediction statement segment(s) contains invalid proposal(s)')


# PredictionBet Statement Update (with segments)
# TODO add or remove
def poll_prediction_statement_update(user: Union[int, User], prediction_statement_id: int) -> None:
    prediction_statement = get_object(PollPredictionStatement, id=prediction_statement_id, active=True)
    group_user = group_user_permissions(user=user, group=prediction_statement.poll.created_by.group,
                                        permissions=['prediction_statement_update', 'admin'])

    prediction_statement.poll.check_phase('prediction_statement', 'dynamic')

    if not prediction_statement.created_by == group_user:
        raise ValidationError('Prediction statement not created by user')


def poll_prediction_statement_delete(user: Union[int, User], prediction_statement_id: int) -> None:
    prediction_statement = get_object(PollPredictionStatement, id=prediction_statement_id, active=True)
    group_user = group_user_permissions(user=user, group=prediction_statement.poll.created_by.group,
                                        permissions=['prediction_statement_delete', 'admin'])

    prediction_statement.poll.check_phase('prediction_statement', 'dynamic')

    if not prediction_statement.created_by == group_user:
        raise ValidationError('Prediction statement not created by user')

    prediction_statement.active = False
    prediction_statement.save()


def poll_prediction_bet_create(user: Union[int, User],
                               prediction_statement_id: int,
                               score: int,
                               blockchain_id: int = None) -> int:
    prediction_statement = get_object(PollPredictionStatement, id=prediction_statement_id)
    group_user = group_user_permissions(user=user, group=prediction_statement.poll.created_by.group,
                                        permissions=['prediction_bet_create', 'admin'])

    prediction_statement.poll.check_phase('prediction_bet', 'dynamic')

    prediction = PollPredictionBet(created_by=group_user,
                                   prediction_statement=prediction_statement,
                                   score=score,
                                   blockchain_id=blockchain_id)
    prediction.full_clean()
    prediction.save()

    return prediction.id


def poll_prediction_bet_update(user: Union[int, User], prediction_statement_id: int, data) -> int:
    try:
        prediction = PollPredictionBet.objects.get(prediction_statement_id=prediction_statement_id,
                                                   created_by__user=user)

    except PollPredictionBet.DoesNotExist:
        return poll_prediction_bet_create(user=user,
                                          prediction_statement_id=prediction_statement_id,
                                          **data)

    group_user = group_user_permissions(user=user, group=prediction.prediction_statement.poll.created_by.group,
                                        permissions=['prediction_bet_update', 'admin'])

    prediction.prediction_statement.poll.check_phase('prediction_bet', 'dynamic')

    if not prediction.created_by == group_user:
        raise ValidationError('Prediction bet not created by user')

    non_side_effect_fields = ['score']
    prediction, has_updated = model_update(instance=prediction,
                                           fields=non_side_effect_fields,
                                           data=data)
    prediction.full_clean()
    prediction.save()

    return prediction.id


def poll_prediction_bet_delete(user: Union[int, User], prediction_statement_id: int):
    prediction = get_object(PollPredictionBet, prediction_statement_id=prediction_statement_id, created_by__user=user)
    group_user = group_user_permissions(user=user, group=prediction.prediction_statement.poll.created_by.group,
                                        permissions=['prediction_bet_delete', 'admin'])

    prediction.prediction_statement.poll.check_phase('prediction_bet', 'dynamic')

    if not prediction.created_by == group_user:
        raise ValidationError('Prediction bet not created by user')

    prediction.delete()


def poll_prediction_statement_vote_create(user: Union[int, User], prediction_statement_id: int, vote: bool):
    prediction_statement = get_object(PollPredictionStatement, id=prediction_statement_id)
    group_user = group_user_permissions(user=user, group=prediction_statement.poll.created_by.group)

    prediction_statement.poll.check_phase('prediction_vote', 'result')

    prediction_vote = PollPredictionStatementVote(created_by=group_user,
                                                  prediction_statement=prediction_statement,
                                                  vote=vote)
    prediction_vote.full_clean()
    prediction_vote.save()

    update_poll_prediction_statement_outcomes(poll_prediction_statement_ids=prediction_statement_id)


def poll_prediction_statement_vote_update(user: Union[int, User],
                                          prediction_statement_id: int,
                                          data) -> PollPredictionStatementVote:
    prediction_statement_vote = get_object(PollPredictionStatementVote,
                                           prediction_statement_id=prediction_statement_id,
                                           created_by__user=user)
    group_user = group_user_permissions(user=user,
                                        group=prediction_statement_vote.prediction_statement.poll.created_by.group)

    prediction_statement_vote.prediction_statement.poll.check_phase('prediction_vote', 'result')

    if prediction_statement_vote.created_by != group_user:
        raise ValidationError('Prediction statement vote not created by user')

    non_side_effect_fields = ['vote']
    prediction_statement_vote, has_updated = model_update(instance=prediction_statement_vote,
                                                          fields=non_side_effect_fields,
                                                          data=data)

    update_poll_prediction_statement_outcomes(poll_prediction_statement_ids=prediction_statement_id)

    return prediction_statement_vote


def poll_prediction_statement_vote_delete(user: Union[int, User], prediction_statement_id: int):
    prediction_statement_vote = get_object(PollPredictionStatementVote,
                                           prediction_statement_id=prediction_statement_id,
                                           created_by__user=user)
    group_user = group_user_permissions(user=user,
                                        group=prediction_statement_vote.prediction_statement.poll.created_by.group)

    prediction_statement_vote.prediction_statement.poll.check_phase('prediction_vote', 'result')

    if prediction_statement_vote.created_by != group_user:
        raise ValidationError('Prediction statement vote not created by user')

    prediction_statement_vote.delete()


def update_poll_prediction_statement_outcomes(poll_prediction_statement_ids: list[int] | int) -> None:
    if isinstance(poll_prediction_statement_ids, int):
        poll_prediction_statement_ids = [poll_prediction_statement_ids]

    qs_filter = PollPredictionStatement.objects.filter(id__in=poll_prediction_statement_ids)

    outcome_score = PollPredictionStatement.objects.filter(id=OuterRef('id')).annotate(
        has_votes=Count('pollpredictionstatementvote'),
        outcome_sum=Sum(Case(When(pollpredictionstatementvote__vote=True, then=1),
                             When(pollpredictionstatementvote__vote=False, then=-1),
                             default=0,
                             output_field=models.IntegerField())),

        outcome_score=Case(When(has_votes=0, then=None),
                           When(outcome_sum__gt=0, then=True),
                           When(outcome_sum__lt=0, then=False),
                           default=None,
                           output_field=models.BooleanField())).values("outcome_score")

    qs_filter.update(outcome=Subquery(outcome_score))
