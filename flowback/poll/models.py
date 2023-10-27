from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, F, Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from backend.settings import SCORE_VOTE_CEILING, SCORE_VOTE_FLOOR
from flowback.prediction.models import (PredictionBet,
                                        PredictionStatement,
                                        PredictionStatementSegment,
                                        PredictionStatementVote)
from flowback.comment.services import comment_section_create
from flowback.common.models import BaseModel
from flowback.group.models import Group, GroupUser, GroupUserDelegatePool, GroupTags
from flowback.comment.models import CommentSection
import pgtrigger


# Create your models here.
class Poll(BaseModel):
    class PollType(models.IntegerChoices):
        RANKING = 1, _('ranking')
        FOR_AGAINST = 2, _('for_against')
        SCHEDULE = 3, _('schedule')
        CARDINAL = 4, _('cardinal')

    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)

    # General information
    title = models.CharField(max_length=255)
    description = models.TextField()
    poll_type = models.IntegerField(choices=PollType.choices)
    quorum = models.IntegerField(default=None, null=True, blank=True,
                                 validators=[MinValueValidator(0), MaxValueValidator(100)])
    tag = models.ForeignKey(GroupTags, on_delete=models.CASCADE, null=True, blank=True)
    pinned = models.BooleanField(default=False)

    # Determines the visibility of this poll
    active = models.BooleanField(default=True)

    # Determines if poll is visible outside of group
    public = models.BooleanField(default=False)

    # Poll Phases
    start_date = models.DateTimeField()  # Poll Start
    area_vote_end_date = models.DateTimeField()  # Area Selection Phase
    proposal_end_date = models.DateTimeField()  # Proposal Phase~
    prediction_statement_end_date = models.DateTimeField()  # Prediction Phase
    prediction_bet_end_date = models.DateTimeField()  # Prediction Betting Phase
    delegate_vote_end_date = models.DateTimeField()  # Delegate Voting Phase
    vote_end_date = models.DateTimeField()  # Voting Phase
    end_date = models.DateTimeField()  # Result Phase, Prediction Vote afterward indefinitely

    """
    Poll Status Code
    0 - Ongoing
    1 - Finished
    -1 - Failed Quorum
    """
    status = models.IntegerField(default=0)
    result = models.BooleanField(default=False)

    # Comment section
    comment_section = models.ForeignKey(CommentSection, default=comment_section_create, on_delete=models.DO_NOTHING)

    # Optional dynamic counting support
    participants = models.IntegerField(default=0)
    dynamic = models.BooleanField()

    @property
    def labels(self) -> tuple:
        return ((self.start_date, 'start date', 'area_vote'),
                (self.area_vote_end_date, 'area vote end date', 'proposal'),
                (self.proposal_end_date, 'proposal end date', 'prediction_statement'),
                (self.prediction_statement_end_date, 'prediction statement end date', 'prediction_bet'),
                (self.prediction_bet_end_date, 'prediction bet end date', 'delegate_vote'),
                (self.delegate_vote_end_date, 'delegate vote end date', 'vote'),
                (self.vote_end_date, 'vote end date', 'result'),
                (self.end_date, 'end date', 'prediction_vote'))

    def clean(self):
        labels = self.labels
        for x in range(len(labels) - 1):
            if labels[x][0] > labels[x+1][0]:
                raise ValidationError(f'{labels[x][1].title()} is greater than {labels[x+1][1]}')

    class Meta:
        constraints = [models.CheckConstraint(check=Q(area_vote_end_date__gte=F('start_date')),
                                              name='areavoteenddategreaterthanstartdate_check'),
                       models.CheckConstraint(check=Q(proposal_end_date__gte=F('area_vote_end_date')),
                                              name='proposalenddategreaterthanareavoteenddate_check'),
                       models.CheckConstraint(check=Q(prediction_statement_end_date__gte=F('proposal_end_date')),
                                              name='predictionstatementenddategreaterthanproposalenddate_check'),
                       models.CheckConstraint(check=Q(prediction_bet_end_date__gte=F('prediction_statement_end_date')),
                                              name='predictionbetenddategreaterthanpredictionstatementeneddate_check'),
                       models.CheckConstraint(check=Q(delegate_vote_end_date__gte=F('prediction_bet_end_date')),
                                              name='delegatevoteenddategreaterthanpredictionbetenddate_check'),
                       models.CheckConstraint(check=Q(vote_end_date__gte=F('delegate_vote_end_date')),
                                              name='voteenddategreaterthandelegatevoteenddate_check'),
                       models.CheckConstraint(check=Q(end_date__gte=F('vote_end_date')),
                                              name='enddategreaterthanvoteenddate_check')]

    @property
    def current_phase(self) -> str:
        labels = self.labels
        current_time = timezone.now()

        for x in reversed(range(len(labels))):
            if current_time > labels[x][0]:
                return labels[x][2]

        return 'waiting'

    def check_phase(self, phase: str):
        current_phase = self.current_phase
        if current_phase != phase:
            raise ValidationError(f'Poll is not in {phase}, currently in {current_phase}')


class PollProposal(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)


class PollProposalTypeSchedule(BaseModel):
    proposal = models.OneToOneField(PollProposal, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()


class PollVoting(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('created_by', 'poll')


class PollDelegateVoting(BaseModel):
    created_by = models.ForeignKey(GroupUserDelegatePool, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('created_by', 'poll')


class PollVotingTypeRanking(BaseModel):
    author = models.ForeignKey(PollVoting, null=True, blank=True, on_delete=models.CASCADE)
    author_delegate = models.ForeignKey(PollDelegateVoting, null=True, blank=True, on_delete=models.CASCADE)

    proposal = models.ForeignKey(PollProposal, on_delete=models.CASCADE)
    priority = models.IntegerField()  # Raw vote score
    score = models.IntegerField(default=0)  # Calculated vote score (delegate only)

    class Meta:
        unique_together = (('author', 'priority'), ('author_delegate', 'priority'),
                           ('author', 'proposal'), ('author_delegate', 'proposal'))

        # Either author or author_delegate can be assigned, not both.

        triggers = [
            pgtrigger.Protect(
                name='protects_author_or_author_delegate',
                operation=pgtrigger.Insert | pgtrigger.Update,
                condition=(pgtrigger.Q(new__author__isnull=True, new__author_delegate__isnull=True)
                           | pgtrigger.Q(new__author__isnull=False, new__author_delegate__isnull=False))
            )
        ]


class PollVotingTypeCardinal(BaseModel):
    author = models.ForeignKey(PollVoting, null=True, blank=True, on_delete=models.CASCADE)
    author_delegate = models.ForeignKey(PollDelegateVoting, null=True, blank=True, on_delete=models.CASCADE)

    proposal = models.ForeignKey(PollProposal, on_delete=models.CASCADE)
    score = models.IntegerField()  # Raw vote score

    def clean(self):
        if SCORE_VOTE_CEILING is not None and self.score >= SCORE_VOTE_CEILING:
            raise ValidationError(f'Voting scores exceeds ceiling bounds (currently set at {SCORE_VOTE_CEILING})')

        if SCORE_VOTE_FLOOR is not None and self.score <= SCORE_VOTE_FLOOR:
            raise ValidationError(f'Voting scores exceeds floor bounds (currently set at {SCORE_VOTE_FLOOR})')

    class Meta:
        unique_together = (('author', 'proposal'), ('author_delegate', 'proposal'))

        # Either author or author_delegate can be assigned, not both.

        triggers = [
            pgtrigger.Protect(
                name='protects_author_or_author_delegate',
                operation=pgtrigger.Insert | pgtrigger.Update,
                condition=(pgtrigger.Q(new__author__isnull=True, new__author_delegate__isnull=True)
                           | pgtrigger.Q(new__author__isnull=False, new__author_delegate__isnull=False))
            )
        ]


class PollVotingTypeForAgainst(BaseModel):
    author = models.ForeignKey(PollVoting, null=True, blank=True, on_delete=models.CASCADE)
    author_delegate = models.ForeignKey(PollDelegateVoting, null=True, blank=True, on_delete=models.CASCADE)

    proposal = models.ForeignKey(PollProposal, on_delete=models.CASCADE)
    vote = models.BooleanField()  # Raw vote score, 0 = Against, 1 = For
    score = models.IntegerField(default=0)  # Calculated vote score (delegate only)

    class Meta:
        unique_together = (('author', 'proposal'), ('author_delegate', 'proposal'))

        # Either author or author_delegate can be assigned, not both.

        triggers = [
            pgtrigger.Protect(
                name='protects_author_or_author_delegate',
                operation=pgtrigger.Insert | pgtrigger.Update,
                condition=(pgtrigger.Q(new__author__isnull=True, new__author_delegate__isnull=True)
                           | pgtrigger.Q(new__author__isnull=False, new__author_delegate__isnull=False))
            )
        ]


class PollAreaStatement(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)


class PollAreaStatementSegment(BaseModel):
    poll_area_statement = models.ForeignKey(PollAreaStatement, on_delete=models.CASCADE)
    tag = models.ForeignKey(GroupTags, on_delete=models.CASCADE)


class PollAreaStatementVote(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    poll_area_statement = models.ForeignKey(PollAreaStatement, on_delete=models.CASCADE)
    vote = models.BooleanField()

    class Meta:
        unique_together = ('created_by', 'poll_area_statement')


class PollPredictionStatement(PredictionStatement):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    def clean(self):
        if self.poll.end_date > self.end_date:
            raise ValidationError('Poll ends earlier than prediction statement end date')

    @receiver(post_delete, sender=PollProposal)
    def clean_prediction_statement(sender, instance: PollProposal, **kwargs):
        PollPredictionStatement.objects.filter(poll=instance.poll)\
                                        .annotate(segment_count=Count('pollpredictionstatementsegment'))\
                                        .filter(segment_count__lt=1)\
                                        .delete()


class PollPredictionStatementSegment(PredictionStatementSegment):
    prediction_statement = models.ForeignKey(PollPredictionStatement, on_delete=models.CASCADE)
    proposal = models.ForeignKey(PollProposal, on_delete=models.CASCADE)


class PollPredictionStatementVote(PredictionStatementVote):
    prediction_statement = models.ForeignKey(PollPredictionStatement, on_delete=models.CASCADE)
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('prediction_statement', 'created_by')


class PollPredictionBet(PredictionBet):
    prediction_statement = models.ForeignKey(PollPredictionStatement, on_delete=models.CASCADE)
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('prediction_statement', 'created_by')

    @receiver(post_save, sender=PredictionStatement)
    def reset_prediction_prediction(sender, instance: PredictionStatement, **kwargs):
        PollPredictionBet.objects.filter(prediction_statement=instance).delete()

    @receiver(post_save, sender=PollProposal)
    def reset_prediction_proposal(sender, instance: PollProposal, **kwargs):
        PollPredictionBet.objects.filter(prediction_statement__pollpredictionstatementsegment__proposal=instance).delete()
