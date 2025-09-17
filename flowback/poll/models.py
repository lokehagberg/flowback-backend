from django.db import models
from django.utils.translation import gettext_lazy as _
from flowback.common.models import BaseModel
from flowback.group.models import Group, GroupUser, GroupUserDelegatePool, GroupTags
import pgtrigger


# Create your models here.
class Poll(BaseModel):
    class PollType(models.IntegerChoices):
        RANKING = 1, _('ranking')
        # FOR_AGAINST = 2, _('for_against')
        # CARDINAL = 3, _('cardinal')

    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)

    # General information
    title = models.CharField(max_length=255)
    description = models.TextField()
    poll_type = models.IntegerField(choices=PollType.choices)
    tag = models.ForeignKey(GroupTags, on_delete=models.CASCADE, null=True, blank=True)

    # Determines the visibility of this poll
    active = models.BooleanField(default=True)

    # Determines if poll is visible outside of group
    public = models.BooleanField(default=False)

    # Determines the state of this poll
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    finished = models.BooleanField(default=False)
    result = models.BooleanField(default=False)

    # Optional dynamic counting support
    participants = models.IntegerField(default=0)
    dynamic = models.BooleanField()


class PollProposal(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)


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
        unique_together = (('author', 'priority'), ('author_delegate', 'priority'))

        # Either author or author_delegate can be assigned, not both.

        triggers = [
            pgtrigger.Protect(
                name='protects_author_or_author_delegate',
                operation=pgtrigger.Insert | pgtrigger.Update,
                condition=(pgtrigger.Q(new__author__isnull=True, new__author_delegate__isnull=True)
                           | pgtrigger.Q(new__author__isnull=False, new__author_delegate__isnull=False))
            )
        ]
