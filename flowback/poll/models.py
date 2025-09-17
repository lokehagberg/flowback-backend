from django.db import models
from django.utils.translation import gettext_lazy as _
from flowback.common.models import BaseModel
from flowback.group.models import Group, GroupUser


# Create your models here.
class Poll(BaseModel):
    class PollType(models.IntegerChoices):
        RANKING = 1, _('Ranking')
        # FOR_AGAINST = 2, _('For/Against')
        # CARDINAL = 3, _('Cardinal')

    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)

    # General information
    title = models.CharField(max_length=255)
    description = models.TextField()
    poll_type = models.IntegerField(choices=PollType.choices)

    # Determines the visibility of this poll
    active = models.BooleanField(default=True)

    # Determines the state of this poll
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    finished = models.BooleanField(default=False)
    result = models.BooleanField(default=False)

    # Optional dynamic counting support
    live_count = models.IntegerField(default=0)
    dynamic = models.BooleanField()


class PollProposal(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    value = models.TextField(null=True, blank=True)


class PollVoting(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)

    proposal = models.ForeignKey(PollProposal, on_delete=models.CASCADE)
    value = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('created_by', 'proposal')
