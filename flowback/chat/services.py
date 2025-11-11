from django.contrib.admin import action
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from flowback.chat.models import MessageChannel, Message, MessageChannelParticipant, MessageFileCollection, \
    MessageChannelTopic
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from backend.settings import TESTING
from flowback.common.services import get_object, model_update
from flowback.files.models import FileCollection
from flowback.files.services import upload_collection
from flowback.user.models import User
from flowback.user.serializers import BasicUserSerializer


def user_message_channel_permission(*, user: User, channel: MessageChannel):
    return get_object(MessageChannelParticipant, user=user, channel=channel, active=True,
                      error_message="User is not participating in this channel")


def message_create(*,
                   user_id: int,
                   channel_id: int,
                   message: str,
                   attachments_id: int = None,
                   parent_id: int = None,
                   topic_id: int = None):
    user = get_object(User, id=user_id)
    channel = get_object(MessageChannel, id=channel_id)
    parent = get_object(Message, id=parent_id, raise_exception=False)

    if parent and (parent.channel_id != channel_id or parent.topic_id != topic_id):
        return ValidationError("Parent does not exist")

    # Check whether user is a participant or not
    user_message_channel_permission(user=user, channel=channel)

    if attachments_id:
        attachments = get_object(MessageFileCollection, id=attachments_id)

        if attachments.user != user and attachments.channel_id != channel_id:
            raise ValidationError("Unauthorized usage of Attachments")

    message = Message(user=user,
                      channel=channel,
                      message=message,
                      attachments_id=attachments_id,
                      parent=parent,
                      topic_id=topic_id)

    message.full_clean()
    message.save()

    return message


def message_update(*, user_id: int, message_id: int, **data):
    user = get_object(User, id=user_id)
    message = get_object(Message, id=message_id, active=True)

    if not user == message.user:
        raise ValidationError('User is not author of message')

    fields = ['message']

    return model_update(instance=message,
                        fields=fields,
                        data=data)


def message_delete(*, user_id: int, message_id: int):
    user = get_object(User, id=user_id)
    message = get_object(Message, id=message_id, active=True)

    if not user == message.user:
        raise ValidationError('User is not author of message')

    message.message = ""
    message.active = False
    message.save()

    return message


def message_files_upload(*, user_id: int, channel_id: int, files: list) -> MessageFileCollection:
    user = get_object(User, id=user_id)
    channel = get_object(MessageChannel, id=channel_id)
    get_object(MessageChannelParticipant, user=user, channel=channel, active=True)
    upload_to = f"{MessageFileCollection.attachments_upload_to}/{channel.origin_name}"

    file_collection = upload_collection(user_id=user_id, file=files,
                                        upload_to=upload_to)

    message_collection = MessageFileCollection(user=user, channel=channel, file_collection=file_collection)
    message_collection.full_clean()
    message_collection.save()

    return message_collection


def message_channel_userdata_update(*, user_id: int, channel_id: int, **data):
    user = get_object(User, id=user_id)
    channel = get_object(MessageChannel, id=channel_id)

    participant = get_object(MessageChannelParticipant, user=user, channel=channel, active=True)
    response = model_update(instance=participant,
                            fields=['timestamp', 'closed_at'],
                            data=data)

    return response[1]


def message_channel_create(*, origin_name: str, title: str = None):
    channel = MessageChannel(origin_name=origin_name, title=title)
    channel.full_clean()
    channel.save()

    return channel


def message_channel_delete(*, channel_id: int):
    channel = get_object(MessageChannel, id=channel_id)
    channel.delete()


def message_channel_join(*, user_id: int, channel_id: int):
    user = get_object(User, id=user_id)
    channel = get_object(MessageChannel, id=channel_id)

    participant = MessageChannelParticipant(user=user,
                                            channel=channel)
    participant.full_clean()
    participant.save()

    # Notify relevant user channels via ChatConsumer that a user joined
    if not TESTING:
        channel_layer = get_channel_layer()

        payload = dict(
            type="message",
            method="message_channel_join",
            channel_id=channel.id,
            channel_title=channel.title,
            users=BasicUserSerializer(channel.users, many=True),
            origin_name=channel.origin_name,
            user_id=user.id,
            username=user.username,
        )

        for user in channel.users.all():
            async_to_sync(channel_layer.group_send)(f"user_{user.id}", payload)

    return participant


def message_channel_leave(*, user_id: int, channel_id: int):
    user = get_object(User, id=user_id)
    channel = get_object(MessageChannel, id=channel_id)
    participant = get_object(MessageChannelParticipant, user=user, channel=channel)

    participant.delete()


def message_channel_topic_create(*, channel_id: int, topic_name: str, hidden: bool = False):
    channel = get_object(MessageChannel, id=channel_id)
    topic = MessageChannelTopic(channel=channel, name=topic_name, hidden=hidden)
    topic.full_clean()
    topic.save()

    return topic


def message_channel_topic_delete(*, channel_id: int, topic_id: int):
    topic = get_object(MessageChannel, channel_id=channel_id, id=topic_id)
    topic.delete()
