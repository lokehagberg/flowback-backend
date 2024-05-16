from django.db import models
from django.db.models import Q

from flowback.common.models import BaseModel
from flowback.files.models import FileCollection
from flowback.user.models import User


class CommentSection(BaseModel):
    active = models.BooleanField(default=True)


class Comment(BaseModel):
    comment_section = models.ForeignKey(CommentSection, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(max_length=10000, null=True, blank=True)
    attachments = models.ForeignKey(FileCollection, on_delete=models.SET_NULL, null=True, blank=True)
    edited = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    score = models.IntegerField(default=0)

    class Meta:
        constraints = [models.CheckConstraint(check=Q(attachments__isnull=False) | Q(message__isnull=False),
                                              name='comment_data_check')]
