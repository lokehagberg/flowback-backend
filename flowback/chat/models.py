from django.db import models
from django.core.exceptions import ValidationError
import pgtrigger

from flowback.common.models import BaseModel
from flowback.user.models import User
from flowback.group.models import GroupUser


class GroupMessage(BaseModel):
    group_user = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    message = models.TextField()


class GroupMessageUserData(BaseModel):
    group_user = models.OneToOneField(GroupUser, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()


class DirectMessage(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='directmessage_user')
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name='directmessage_target')
    message = models.TextField()

    def clean(self):
        if self.user == self.target:
            raise ValidationError("user and target cannot be the same")


class DirectMessageUserData(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='directmessageuserdata_user')
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name='directmessageuserdata_target')
    timestamp = models.DateTimeField()

    def clean(self):
        if self.user == self.target:
            raise ValidationError("user and target cannot be the same")

    class Meta:
        unique_together = 'user', 'target', 'timestamp'
