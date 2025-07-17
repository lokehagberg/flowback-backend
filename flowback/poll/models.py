from datetime import datetime

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q, F, Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from backend.settings import FLOWBACK_SCORE_VOTE_CEILING, FLOWBACK_SCORE_VOTE_FLOOR, DEBUG
from flowback.files.models import FileCollection
from flowback.notification.models import NotifiableModel, NotificationChannel
from flowback.prediction.models import (PredictionBet,
                                        PredictionStatement,
                                        PredictionStatementSegment,
                                        PredictionStatementVote)
from flowback.common.models import BaseModel
from flowback.group.models import Group, GroupUser, GroupUserDelegatePool, GroupTags, WorkGroup
from flowback.comment.models import CommentSection, comment_section_create_model_default
import pgtrigger

from flowback.schedule.models import Schedule, ScheduleEvent
from flowback.schedule.services import create_schedule


# Create your models here.
class Poll(BaseModel, NotifiableModel):
    class PollType(models.IntegerChoices):
        RANKING = 1, _('ranking')
        FOR_AGAINST = 2, _('for_against')
        SCHEDULE = 3, _('schedule')
        CARDINAL = 4, _('cardinal')

    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)

    # General information
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    attachments = models.ForeignKey(FileCollection, on_delete=models.SET_NULL, null=True, blank=True)
    poll_type = models.IntegerField(choices=PollType.choices)
    quorum = models.IntegerField(default=None, null=True, blank=True,
                                 validators=[MinValueValidator(0), MaxValueValidator(100)])
    tag = models.ForeignKey(GroupTags, on_delete=models.CASCADE, null=True, blank=True)
    pinned = models.BooleanField(default=False)

    # Determines the visibility of this poll
    active = models.BooleanField(default=True)

    # Determines if poll is visible outside of group
    public = models.BooleanField(default=False)
    allow_fast_forward = models.BooleanField(default=False)
    interval_mean_absolute_correctness = models.DecimalField(
        max_digits=12,
        decimal_places=9,
        null=True,
        blank=True,
        help_text="Calculates after end date, will contain the current Interval Mean Absolute Correctness "
                  "at the time of calculation.")

    # Poll Phases
    start_date = models.DateTimeField()  # Poll Start
    area_vote_end_date = models.DateTimeField(null=True, blank=True)  # Area Selection Phase
    proposal_end_date = models.DateTimeField(null=True, blank=True)  # Proposal Phase
    prediction_statement_end_date = models.DateTimeField(null=True, blank=True)  # Prediction Phase
    prediction_bet_end_date = models.DateTimeField(null=True, blank=True)  # Prediction Betting Phase
    delegate_vote_end_date = models.DateTimeField(null=True, blank=True)  # Delegate Voting Phase
    vote_end_date = models.DateTimeField(null=True, blank=True)  # Voting Phase
    end_date = models.DateTimeField()  # Result Phase, Prediction Vote afterward indefinitely

    blockchain_id = models.PositiveIntegerField(null=True, blank=True, default=None)
    work_group = models.ForeignKey(WorkGroup, on_delete=models.CASCADE, null=True, blank=True)

    """
    Poll Status Code
    0 - Ongoing
    1 - Finished
    -1 - Failed Quorum
    """
    status = models.IntegerField(default=0)

    """
    Prediction Status Code
    0 - Idle
    1 - Finished
    2 - Calculating Combined Bets
    """
    status_prediction = models.IntegerField(default=0)
    result = models.BooleanField(default=False)

    # Comment section
    comment_section = models.ForeignKey(CommentSection, default=comment_section_create_model_default,
                                        on_delete=models.DO_NOTHING)

    # Optional dynamic counting support
    participants = models.IntegerField(default=0)
    dynamic = models.BooleanField()

    @property
    def finished(self):
        return self.vote_end_date <= timezone.now()

    @property
    def labels(self) -> tuple:
        if self.dynamic:
            if self.poll_type == self.PollType.SCHEDULE:
                return ((self.start_date, 'start_date', 'schedule'),
                        (self.end_date, 'end_date', 'result'))

            else:
                return ((self.start_date, 'start_date', 'dynamic'),
                        (self.end_date, 'end_date', 'result'))

        return ((self.start_date, 'start_date', 'area_vote'),
                (self.area_vote_end_date, 'area_vote_end_date', 'proposal'),
                (self.proposal_end_date, 'proposal_end_date', 'prediction_statement'),
                (self.prediction_statement_end_date, 'prediction_statement_end_date', 'prediction_bet'),
                (self.prediction_bet_end_date, 'prediction_bet_end_date', 'delegate_vote'),
                (self.delegate_vote_end_date, 'delegate_vote_end_date', 'vote'),
                (self.vote_end_date, 'vote_end_date', 'result'),
                (self.end_date, 'end_date', 'prediction_vote'))

    @property
    def time_table(self) -> list:
        labels = [[self.start_date, 'start_date', 'area_vote'],
                  [self.area_vote_end_date, 'area_vote_end_date', 'proposal'],
                  [self.proposal_end_date, 'proposal_end_date', 'prediction_statement'],
                  [self.prediction_statement_end_date, 'prediction_statement_end_date', 'prediction_bet'],
                  [self.prediction_bet_end_date, 'prediction_bet_end_date', 'delegate_vote'],
                  [self.delegate_vote_end_date, 'delegate_vote_end_date', 'vote'],
                  [self.vote_end_date, 'vote_end_date', 'result'],
                  [self.end_date, 'end_date', 'prediction_vote']]

        if self.dynamic:
            if self.poll_type == self.PollType.SCHEDULE:
                labels[0][2] = 'schedule'
                labels[6][2] = 'result_default'
                labels[7][2] = 'result'

            else:
                labels[0][2] = 'dynamic'
                labels[6][2] = 'result_default'
                labels[7][2] = 'result'

        return labels

    def clean(self):
        labels = self.labels
        for x in range(len(labels) - 1):
            phase = labels[x]
            next_phase = labels[x + 1]
            if phase[0] >= next_phase[0]:
                raise ValidationError(f'{phase[1].replace("_", " ").title()} '
                                      f'starts after {next_phase[1].replace("_", " ").title()}')
            elif phase[0] + timezone.timedelta(seconds=self.created_by.group.poll_phase_minimum_space) >= next_phase[0]:
                raise ValidationError(f'The time between phases {phase[1].replace("_", " ").title()} '
                                      f'and {next_phase[1].replace("_", " ").title()} is below minimum')

    class Meta:
        constraints = [models.CheckConstraint(check=Q(Q(area_vote_end_date__isnull=True)
                                                      | Q(area_vote_end_date__gte=F('start_date'))),
                                              name='areavoteenddategreaterthanstartdate_check'),
                       models.CheckConstraint(check=Q(Q(proposal_end_date__isnull=True)
                                                      | Q(proposal_end_date__gte=F('area_vote_end_date'))),
                                              name='proposalenddategreaterthanareavoteenddate_check'),
                       models.CheckConstraint(check=Q(Q(prediction_statement_end_date__isnull=True)
                                                      | Q(prediction_statement_end_date__gte=F('proposal_end_date'))),
                                              name='predictionstatementenddategreaterthanproposalenddate_check'),
                       models.CheckConstraint(check=Q(Q(prediction_bet_end_date__isnull=True)
                                                      | Q(
                           prediction_bet_end_date__gte=F('prediction_statement_end_date'))),
                                              name='predictionbetenddategreaterthanpredictionstatementeneddate_check'),
                       models.CheckConstraint(check=Q(Q(delegate_vote_end_date__isnull=True)
                                                      | Q(delegate_vote_end_date__gte=F('prediction_bet_end_date'))),
                                              name='delegatevoteenddategreaterthanpredictionbetenddate_check'),
                       models.CheckConstraint(check=Q(Q(vote_end_date__isnull=True)
                                                      | Q(vote_end_date__gte=F('delegate_vote_end_date'))),
                                              name='voteenddategreaterthandelegatevoteenddate_check'),
                       models.CheckConstraint(check=Q(Q(end_date__isnull=True)
                                                      | Q(end_date__gte=F('vote_end_date'))),
                                              name='enddategreaterthanvoteenddate_check'),

                       models.CheckConstraint(check=~Q(Q(poll_type=3) & Q(dynamic=False)),
                                              name='polltypeisscheduleanddynamic_check')]

    @property
    def schedule_origin(self):
        return 'group_poll'

    @property
    def current_phase(self) -> str:
        labels = self.labels
        current_time = timezone.now()

        for x in reversed(range(len(labels))):
            if current_time >= labels[x][0]:
                return labels[x][2]

        return 'waiting'

    def get_phase(self, phase: str, field_name=False) -> datetime | str:
        time_table = self.time_table

        for x in reversed(range(len(time_table))):
            if phase == time_table[x][2]:
                if field_name:
                    return time_table[x][1]

                else:
                    return time_table[x][0]

        raise Exception('Phase not found')

    def phase_exist(self, phase: str, raise_exception=True):
        phases = [label[2] for label in self.labels]

        if phase in phases:
            return True

        if raise_exception:
            raise ValidationError(f'Poll phase "{phase}" does not exist')

        return False

    def check_phase(self, *phases: str):
        if not any(self.phase_exist(phase, raise_exception=False) for phase in phases):
            raise ValidationError(f'Action is unavailable for this poll')

        current_phase = self.current_phase
        if current_phase not in phases:
            raise ValidationError(f'Poll is not in {" or ".join(phases)}, currently in {current_phase}')

    NOTIFICATION_DATA_FIELDS = (('poll_id', int),
                                ('poll_title', str),
                                ('group_id', int),
                                ('group_name', str),
                                ('group_image', str, 'The URL path to the image of the group'))

    ## Notification
    @property
    def notification_data(self) -> dict | None:
        return dict(poll_id=self.id,
                    poll_title=self.title,
                    group_id=self.created_by.group.id,
                    group_name=self.created_by.group.name,
                    group_image=self.created_by.group.image)

    def notify_poll(self,
                    action: NotificationChannel.Action,
                    message: str,
                    work_group_id: int,
                    work_group_name: str,
                    subscription_filters: dict):
        """
        Notifies when a poll updates and deletes.
        Also notifies when poll area, prediction and proposal votes have been counted.
        :param action:
        :param message:
        :param work_group_id:
        :param work_group_name:
        :param subscription_filters:
        :return:
        """
        params = locals()
        params.pop('self')

        return self.notification_channel.notify(**params)

    def notify_poll_phase(self,
                          action: NotificationChannel.Action,
                          message: str,
                          work_group_id: int,
                          work_group_name: str,
                          current_phase: str,
                          subscription_filters: dict):
        """
        Notifies when a poll does fast-forward
        """
        params = locals()
        params.pop('self')

        return self.notification_channel.notify(**params)

    def notify_poll_comment(self,
                            action: NotificationChannel.Action,
                            message: str,
                            work_group_id: int,
                            work_group_name: str,
                            subscription_filters: dict,
                            exclude_subscription_filters: dict,
                            comment_message: str):
        """
        Notifies about new comments
        """
        params = locals()
        params.pop('self')

        return self.notification_channel.notify(**params)

    # Signals
    @classmethod
    def post_save(cls, instance, created, update_fields, **kwargs):
        if created and instance.poll_type == cls.PollType.SCHEDULE:
            try:
                schedule = create_schedule(name='group_poll_schedule', origin_name='group_poll', origin_id=instance.id)
                schedule_poll = PollTypeSchedule(poll=instance, schedule=schedule)
                schedule_poll.full_clean()
                schedule_poll.save()

            except Exception as e:
                instance.delete()
                raise Exception('Internal server error when creating poll' + f':\n{e}' if DEBUG else '')

    @classmethod
    def post_delete(cls, instance, **kwargs):
        if hasattr(instance, 'schedule'):
            instance.schedule.delete()


post_save.connect(Poll.post_save, sender=Poll)
post_delete.connect(Poll.post_delete, sender=Poll)


class PollTypeSchedule(BaseModel):
    poll = models.OneToOneField(Poll, on_delete=models.CASCADE)
    schedule = models.OneToOneField(Schedule, on_delete=models.CASCADE)


class PollProposal(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    attachments = models.ForeignKey(FileCollection, on_delete=models.CASCADE, null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)

    blockchain_id = models.PositiveIntegerField(null=True, blank=True, default=None)

    @property
    def schedule_origin(self):
        return 'group_poll_proposal'


class PollProposalTypeSchedule(BaseModel):
    proposal = models.OneToOneField(PollProposal, on_delete=models.CASCADE)
    event = models.OneToOneField(ScheduleEvent, on_delete=models.CASCADE)

    def clean(self):
        if PollProposalTypeSchedule.objects.filter(event__start_date=self.event.start_date,
                                                   event__end_date=self.event.end_date,
                                                   proposal__poll=self.proposal.poll).exists():
            raise ValidationError('Proposal event with same start_date and end_date already exists')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['proposal', 'event'], name='unique_proposaltypeschedule')]

    @classmethod
    def post_delete(cls, instance, **kwargs):
        instance.event.delete()


post_delete.connect(PollProposalTypeSchedule.post_delete, PollProposalTypeSchedule)


class PollVoting(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('created_by', 'poll')


class PollDelegateVoting(BaseModel):
    created_by = models.ForeignKey(GroupUserDelegatePool, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    mandate = models.IntegerField(default=0)

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
    raw_score = models.IntegerField(default=0)  # Raw vote score
    score = models.IntegerField(null=True, blank=True)

    def clean(self):
        if FLOWBACK_SCORE_VOTE_CEILING is not None and self.raw_score >= FLOWBACK_SCORE_VOTE_CEILING:
            raise ValidationError(
                f'Voting scores exceeds ceiling bounds (currently set at {FLOWBACK_SCORE_VOTE_CEILING})')

        if FLOWBACK_SCORE_VOTE_FLOOR is not None and self.raw_score <= FLOWBACK_SCORE_VOTE_FLOOR:
            raise ValidationError(f'Voting scores exceeds floor bounds (currently set at {FLOWBACK_SCORE_VOTE_FLOOR})')

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


# TODO Area requires refactor
class PollAreaStatement(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)


class PollAreaStatementSegment(BaseModel):
    poll_area_statement = models.ForeignKey(PollAreaStatement, on_delete=models.CASCADE)
    tag = models.ForeignKey(GroupTags, on_delete=models.CASCADE)

    def clean(self):
        if self.tag.active is False:
            raise ValidationError("Tag must be active")


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
            raise ValidationError('Poll ends later than prediction statement deadline')

    @receiver(post_delete, sender=PollProposal)
    def clean_prediction_statement(sender, instance: PollProposal, **kwargs):
        PollPredictionStatement.objects.filter(poll=instance.poll) \
            .annotate(segment_count=Count('pollpredictionstatementsegment')) \
            .filter(segment_count__lt=1) \
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
        PollPredictionBet.objects.filter(
            prediction_statement__pollpredictionstatementsegment__proposal=instance).delete()


class PollPhaseTemplate(BaseModel):
    created_by_group_user = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    poll_type = models.IntegerField(choices=Poll.PollType.choices)
    poll_is_dynamic = models.BooleanField(default=False)

    # We store integers that define seconds since previous phase in seconds
    # Assume area_vote_time_delta is time since poll start_date
    area_vote_time_delta = models.IntegerField(null=True, blank=True)  # Area Vote Phase
    proposal_time_delta = models.IntegerField(null=True, blank=True)  # Proposal Phase
    prediction_statement_time_delta = models.IntegerField(null=True, blank=True)  # Prediction Phase
    prediction_bet_time_delta = models.IntegerField(null=True, blank=True)  # Prediction Bet Phase
    delegate_vote_time_delta = models.IntegerField(null=True, blank=True)  # Delegate Vote Phase
    vote_time_delta = models.IntegerField(null=True, blank=True)  # Vote Phase
    end_time_delta = models.IntegerField()  # Result Phase

    class Meta:
        constraints = [
            # Check if cardinal polls that isn't dynamic don't have any null values
            models.CheckConstraint(check=~Q(Q(Q(poll_type=4) & Q(poll_is_dynamic=False))
                                            & ~Q(Q(area_vote_time_delta__isnull=False)
                                                 | Q(proposal_time_delta__isnull=False)
                                                 | Q(prediction_statement_time_delta__isnull=False)
                                                 | Q(prediction_bet_time_delta__isnull=False)
                                                 | Q(delegate_vote_time_delta__isnull=False)
                                                 | Q(vote_time_delta__isnull=False)
                                                 | Q(end_time_delta__isnull=False))),
                                   name='pollphasetemplatecardinalisvalid_check'),

            # Check if schedule poll or dynamic poll have null values except for vote_time_delta and end_time_delta
            models.CheckConstraint(check=~Q(Q(Q(poll_type=3) | Q(poll_is_dynamic=True))
                                            & Q(Q(area_vote_time_delta__isnull=True)
                                                | Q(proposal_time_delta__isnull=True)
                                                | Q(prediction_statement_time_delta__isnull=True)
                                                | Q(prediction_bet_time_delta__isnull=True)
                                                | Q(delegate_vote_time_delta__isnull=True)
                                                | Q(vote_time_delta__isnull=False)
                                                | Q(end_time_delta__isnull=False))),
                                   name='pollphasetemplatescheduleordynamicisvalid_check')
        ]
