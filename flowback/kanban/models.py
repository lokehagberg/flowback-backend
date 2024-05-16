from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _

from django.db import models
from flowback.common.models import BaseModel


class Kanban(BaseModel):
    name = models.CharField(max_length=255)
    origin_type = models.CharField(max_length=255)
    origin_id = models.IntegerField()

    class Meta:
        unique_together = ('origin_type', 'origin_id')


class KanbanEntry(BaseModel):
    class KanbanTag(models.IntegerChoices):
        BACKLOG = 1, _('backlog')
        CHOSEN_FOR_EXECUTION = 2, _('chosen_for_execution')
        IN_PROGRESS = 3, _('in_progress')
        EVALUATION = 4, _('evaluation')
        FINISHED = 5, _('finished')

    kanban = models.ForeignKey(Kanban, on_delete=models.CASCADE)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='kanban_entry_created_by')
    assignee = models.ForeignKey('user.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='kanban_entry_assignee')
    end_date = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(validators=[MaxValueValidator(5),
                                               MinValueValidator(1)], default=3)

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    tag = models.IntegerField(choices=KanbanTag.choices)


class KanbanSubscription(BaseModel):
    kanban = models.ForeignKey(Kanban, on_delete=models.CASCADE, related_name='kanban_subscription_kanban')
    target = models.ForeignKey(Kanban, on_delete=models.CASCADE, related_name='kanban_subscription_target')

    class Meta:
        unique_together = ('kanban', 'target')
