from django.db import models
from flowback.common.models import BaseModel
from flowback.group.models import GroupUser


class KanbanEntry(BaseModel):
    class KanbanTag(models.IntegerChoices):
        pass

    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)

    title = models.CharField(max_length=255)
    description = models.TextField()
    tag = models.IntegerField(choices=KanbanTag.choices)
