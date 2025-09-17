from django.db import models
from django.core.exceptions import ValidationError
from flowback.common.models import BaseModel
from flowback.user.models import User
from flowback.group.models import GroupUser


class GroupMessage(BaseModel):
    group_user = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    message = models.TextField()


class DirectMessage(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='directmessage_user')
    target = models.ForeignKey(User, on_delete=models.CASCADE, related_name='directmessage_target')
    message = models.TextField()

    def clean(self):
        if self.user == self.target:
            raise ValidationError("user_one and user_two cannot be the same")
