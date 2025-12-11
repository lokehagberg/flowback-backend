import math

from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from django.db import models
from rest_framework.exceptions import ValidationError

from backend.settings import FLOWBACK_KANBAN_PRIORITY_LIMIT, FLOWBACK_KANBAN_LANES
from flowback.common.models import BaseModel
from flowback.common.validators import FieldNotBlankValidator


class Kanban(BaseModel):
    name = models.CharField(max_length=255, validators=[FieldNotBlankValidator])
    origin_type = models.CharField(max_length=255, validators=[FieldNotBlankValidator])
    origin_id = models.IntegerField()

    class Meta:
        unique_together = ('origin_type', 'origin_id')


class KanbanEntry(BaseModel):
    kanban = models.ForeignKey(Kanban, on_delete=models.CASCADE)
    created_by = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='kanban_entry_created_by')
    assignee = models.ForeignKey('user.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='kanban_entry_assignee')
    end_date = models.DateTimeField(null=True, blank=True)
    priority = models.IntegerField(default=1)
    title = models.CharField(max_length=255, validators=[FieldNotBlankValidator])
    description = models.TextField(null=True, blank=True, validators=[FieldNotBlankValidator])
    attachments = models.ForeignKey('files.FileCollection', on_delete=models.SET_NULL, null=True, blank=True)
    work_group = models.ForeignKey('group.WorkGroup', on_delete=models.CASCADE, null=True, blank=True)
    lane = models.IntegerField(validators=[MinValueValidator(1)])

    def clean(self):
        if self.priority > FLOWBACK_KANBAN_PRIORITY_LIMIT:
            raise ValidationError(f"Kanban priority can't be greater than {FLOWBACK_KANBAN_PRIORITY_LIMIT}")

        if self.lane > len(FLOWBACK_KANBAN_LANES):
            raise ValidationError(f"Kanban lane number can't be greater than {len(FLOWBACK_KANBAN_LANES)}")

    @classmethod
    def pre_save(cls, instance, *args, **kwargs):
        if instance.pk is None and instance.priority is None:
            instance.priority = math.floor(FLOWBACK_KANBAN_PRIORITY_LIMIT / 2)


class KanbanEntryTag(BaseModel):
    name = models.CharField(max_length=255, validators=[FieldNotBlankValidator])


class KanbanSubscription(BaseModel):
    kanban = models.ForeignKey(Kanban, on_delete=models.CASCADE, related_name='kanban_subscription_kanban')
    target = models.ForeignKey(Kanban, on_delete=models.CASCADE, related_name='kanban_subscription_target')

    class Meta:
        unique_together = ('kanban', 'target')
