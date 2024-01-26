from django.shortcuts import get_object_or_404
from django.utils.datetime_safe import datetime
from rest_framework.exceptions import ValidationError

from flowback.chat.models import MessageChannel, Message, MessageChannelParticipant, MessageFileCollection, \
    MessageChannelTopic
from flowback.common.services import get_object, model_update
from flowback.files.models import FileCollection
from flowback.files.services import upload_collection
from flowback.user.models import User


def message_create(*,
                   user_id: int,
                   channel_id: int,
                   message: str,
                   attachments_id: int = None,
                   parent_id: int = None):
    user = get_object(User, user=user_id)
    channel = get_object(MessageChannel, channel=channel_id)
    parent = get_object(Message, id=parent_id, raise_exception=False)

    # Check whether user is a participant or not
    get_object(MessageChannelParticipant, user=user, channel=channel,
               error_message="User is not participating in this channel")

    if parent and parent.channel.id != channel_id:
        raise ValidationError('Parent does not exist')

    if attachments_id:
        attachments = get_object(MessageFileCollection, id=attachments_id)

        if attachments.created_by != user and attachments.channel_id != channel_id:
            raise ValidationError("Unauthorized usage of Attachments")

    message = Message(user=user,
                      channel=channel,
                      message=message,
                      attachments_id=attachments_id,
                      parent=parent)

    message.full_clean()
    message.save()

    return message


def message_update(*, user_id: int, message_id: int, **data):
    user = get_object(User, user=user_id)
    message = get_object(Message, id=message_id)

    if not user == message.user:
        raise ValidationError('User is not author of message')

    fields = ['message']

    model_update(instance=message,
                 fields=fields,
                 data=data)


def message_delete(*, user_id: int, message_id: int):
    user = get_object(User, user=user_id)
    message = get_object(Message, id=message_id)

    if not user == message.user:
        raise ValidationError('User is not author of message')

    message.message = ""
    message.active = False
    message.save()


def message_files_upload(*, user_id: int, channel_id: int, files: list) -> MessageFileCollection:
    user = get_object(User, user=user_id)
    channel = get_object(MessageChannel, id=channel_id)
    get_object(MessageChannelParticipant, user=user, channel=channel)
    upload_to = f"{MessageFileCollection.attachments_upload_to}/{channel.origin_name}"

    file_collection = upload_collection(user_id=user_id, file=files,
                                        upload_to=upload_to)

    message_collection = MessageFileCollection(user=user, channel=channel, file_collection=file_collection)
    message_collection.full_clean()
    message_collection.save()

    return message_collection


def message_channel_userdata_update(*, user_id: int, channel_id: int, **data):
    user = get_object(User, user=user_id)
    channel = get_object(MessageChannel, id=channel_id)

    participant = get_object(MessageChannelParticipant, user=user, channel=channel)
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
    user = get_object(User, user=user_id)
    channel = get_object(MessageChannel, id=channel_id)

    participant = MessageChannelParticipant(user=user,
                                            channel=channel)
    participant.full_clean()
    participant.save()

    return participant


def leave_message_channel(*, user_id: int, channel_id: int):
    user = get_object(User, user=user_id)
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
