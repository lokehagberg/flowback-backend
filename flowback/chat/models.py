from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import models
from django.db.models.signals import post_delete, post_save

from backend.settings import TESTING
from flowback.common.models import BaseModel
from flowback.common.validators import FieldNotBlankValidator
from flowback.files.models import FileCollection


class MessageChannel(BaseModel):
    origin_name = models.CharField(max_length=255, validators=[FieldNotBlankValidator])
    title = models.CharField(max_length=255, null=True, blank=True, validators=[FieldNotBlankValidator])
    users = models.ManyToManyField('user.User', through='chat.MessageChannelParticipant')


# Allows for "channels" inside a group
class MessageChannelTopic(BaseModel):
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, validators=[FieldNotBlankValidator])
    hidden = models.BooleanField(default=False)


class MessageChannelParticipant(BaseModel):
    user = models.ForeignKey('user.User', on_delete=models.CASCADE)
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE)
    closed_at = models.DateTimeField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    @property
    def recent_message(self):
        return self.channel.message_set.filter(active=True, type='message').order_by('-created_at').first()


    class Meta:
        unique_together = ('user', 'channel')


# For image attachments
class MessageFileCollection(BaseModel):
    user = models.ForeignKey('user.User', on_delete=models.CASCADE)
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE)
    file_collection = models.ForeignKey(FileCollection, on_delete=models.CASCADE)

    @property
    def attachments_upload_to(self):
        return 'message'


class Message(BaseModel):
    user = models.ForeignKey('user.User', on_delete=models.CASCADE)
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE)
    type = models.CharField(max_length=255, default='message', validators=[FieldNotBlankValidator])
    topic = models.ForeignKey(MessageChannelTopic, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField(max_length=2000, validators=[FieldNotBlankValidator])
    attachments = models.ForeignKey(MessageFileCollection,
                                    on_delete=models.SET_NULL,
                                    null=True,
                                    blank=True)  # TODO instead of MessageFileCollection, use FileCollection directly
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='message_parent')
    active = models.BooleanField(default=True)
