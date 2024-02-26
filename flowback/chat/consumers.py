import json
from typing import Union

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from flowback.chat.models import MessageChannelParticipant
from flowback.chat.serializers import BasicMessageSerializer, MessageSerializer
from flowback.chat.services import message_create, message_update, message_delete
from flowback.common.services import get_object
from flowback.user.models import User
from flowback.group.models import Group
from flowback.group.services import group_user_permissions
from flowback.user.serializers import BasicUserSerializer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.scope['user'].is_anonymous:
            return await self.close()

        self.user_channel = f"user_{self.user.id}"
        self.participating_channels = await self.get_participating_channels()
        self.participating_channels.append(self.user_channel)
        for channel in self.participating_channels:
            await self.channel_layer.group_add(
                f"{channel}",
                self.channel_name
            )

        await self.accept()

    async def disconnect(self, close_code):
        if self.scope['user'].is_anonymous:
            return await self.close()

        for channel in self.participating_channels:
            await self.channel_layer.group_discard(
                f"{channel}",
                self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data or '{}')

        # Message endpoint
        if data.get('type') == 'message_create':
            await self.message_create(data=data)

        if data.get('type') == 'message_update':
            await self.message_update(data=data)

        if data.get('type') == 'message_delete':
            await self.message_delete(data=data)

        elif data.get('type') == 'connect_channel':
            await self.connect_channel(data=data)

        elif data.get('type') == 'disconnect_channel':
            await self.connect_channel(data=data, disconnect=True)

        return True

    # Send message to WebSocket
    # TODO Check if redundant
    async def message(self, content: dict):
        if content.get('type_override'):
            content['type'] = content.pop('type_override')
        await self.send(text_data=json.dumps(content))

    @database_sync_to_async
    def get_participating_channels(self):
        return list(MessageChannelParticipant.objects.filter(user=self.user).values_list('channel_id', flat=True))

    @staticmethod
    def generate_status_message(message: str, type: str, **kwargs):
        return dict(type="message",
                    type_override=type,
                    message=message,
                    **kwargs)

    async def send_message(self, channel_id, message: Union[dict, str]):
        if isinstance(message, dict):
            if not message.get("type"):
                message["type"] = "message"

        await self.channel_layer.group_send(
            f"{channel_id}",
            message
        )

    @database_sync_to_async
    def _create_message(self, *,
                        user_id: int,
                        channel_id: int,
                        message: str,
                        attachments_id: int = None,
                        parent_id: int = None,
                        topic_id: int = None):

        message = message_create(user_id=user_id, channel_id=channel_id, message=message,
                                 attachments_id=attachments_id, parent_id=parent_id, topic_id=topic_id)

        return MessageSerializer(message).data

    async def message_create(self, data: dict):
        class MessageInputSerializer(serializers.Serializer):
            channel_id = serializers.IntegerField()
            message = serializers.CharField()
            attachments_id = serializers.IntegerField(required=False)
            parent_id = serializers.IntegerField(required=False)
            topic_id = serializers.IntegerField(required=False)

        serializer = MessageInputSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Save message to database
        try:
            message = await self._create_message(user_id=self.user.id,
                                                 **data)

        except ValidationError as e:
            message = self.generate_status_message(channel_id=data.get('channel_id'),
                                                   message=f"{', '.join([x for x in e.detail])}",
                                                   type="error")

            await self.channel_layer.group_send(self.user_channel, message)
            return False

        await self.send_message(channel_id=data.get('channel_id'), message=message)
        return True

    @database_sync_to_async
    def _update_message(self, *,
                        user_id: int,
                        message_id: int,
                        **data):

        update = message_update(user_id=user_id, message_id=message_id, **data)

        return dict(**MessageSerializer(update[0]).data, type_override="message_update")

    async def message_update(self, data: dict):
        class InputSerializer(serializers.Serializer):
            message_id = serializers.IntegerField()
            message = serializers.CharField()

        serializer = InputSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Update message
        try:
            message = await self._update_message(user_id=self.user.id, **data)

        except ValidationError as e:
            message = self.generate_status_message(message=f"{', '.join([x for x in e.detail])}",
                                                   type="message_update",
                                                   status="error")

            await self.send_message(channel_id=self.user_channel, message=message)
            return False

        await self.send_message(channel_id=message['channel_id'], message=message)
        return True

    @database_sync_to_async
    def _delete_message(self, *,
                        user_id: int,
                        message_id: int):
        message = message_delete(user_id=user_id, message_id=message_id)
        return dict(**MessageSerializer(message).data, type_override="message_delete")

    async def message_delete(self, data: dict):
        class InputSerializer(serializers.Serializer):
            message_id = serializers.IntegerField()

        serializer = InputSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Update message
        try:
            message = await self._delete_message(user_id=self.user.id, **data)

        except ValidationError as e:
            message = self.generate_status_message(message_id=data.get('message_id'),
                                                   message=f"{', '.join([x for x in e.detail])}",
                                                   type="message_delete",
                                                   status="error")

            await self.send_message(channel_id=self.user_channel, message=message)
            return False

        await self.send_message(channel_id=message['channel_id'], message=message)
        return True

    async def connect_channel(self, data, disconnect=False):
        class ConnectChannelInputSerializer(serializers.Serializer):
            channel_id = serializers.IntegerField()

        serializer = ConnectChannelInputSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        channel_id = data.get('channel_id')

        if not disconnect and channel_id in await self.get_participating_channels():
            await self.channel_layer.group_add(f"{channel_id}", self.channel_name)
            self.participating_channels.append(f"{channel_id}")

        elif disconnect and channel_id in self.participating_channels:
            await self.channel_layer.group_discard(f"{channel_id}", self.channel_name)

        else:
            await self.channel_layer.group_send(self.user_channel,
                                                dict(channel_id=channel_id,
                                                     type="error",
                                                     message="Unknown operation"))

        return True
