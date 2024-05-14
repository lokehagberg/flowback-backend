from django.db import models

from flowback.common.models import BaseModel
from flowback.files.models import FileCollection
from flowback.user.models import User
from mptt.models import MPTTModel, TreeForeignKey


class MessageChannel(BaseModel):
    origin_name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, null=True, blank=True)


class MessageChannelTopic(BaseModel):
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    hidden = models.BooleanField(default=False)


class MessageChannelParticipant(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE)
    closed_at = models.DateTimeField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'channel')


class MessageFileCollection(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE)
    file_collection = models.ForeignKey(FileCollection, on_delete=models.CASCADE)

    @property
    def attachments_upload_to(self):
        return 'message'


class Message(BaseModel, MPTTModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE)
    topic = models.ForeignKey(MessageChannelTopic, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField(max_length=2000)
    attachments = models.ForeignKey(MessageFileCollection, on_delete=models.SET_NULL, null=True, blank=True)
    parent = TreeForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='message_parent')
    active = models.BooleanField(default=True)

    class MPTTMeta:
        order_insertion_by = ['created_at']