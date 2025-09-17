from django.utils.translation import gettext_lazy as _

from django.db import models
from flowback.common.models import BaseModel
from flowback.group.models import GroupUser


class KanbanEntry(BaseModel):
    class KanbanTag(models.IntegerChoices):
        BACKLOG = 1, _('backlog')
        CHOSEN_FOR_EXECUTION = 2, _('chosen_for_execution')
        IN_PROGRESS = 3, _('in_progress')
        EVALUATION = 4, _('evaluation')
        FINISHED = 5, _('finished')

    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    assignee = models.ForeignKey(GroupUser, on_delete=models.CASCADE, related_name='kanban_entry_assignee')

    title = models.CharField(max_length=255)
    description = models.TextField()
    tag = models.IntegerField(choices=KanbanTag.choices)
