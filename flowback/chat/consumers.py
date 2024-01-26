import json
from typing import Union

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from flowback.chat.models import MessageChannelParticipant
from flowback.chat.services import message_create
from flowback.common.services import get_object
from flowback.user.models import User
from flowback.group.models import Group
from flowback.group.services import group_user_permissions
from flowback.user.serializers import BasicUserSerializer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.scope['user'].is_anonymous:
            await self.close()

        self.user_channel = f"user_{self.user.id}"
        self.participating_channels = await self.get_participating_channels()
        self.participating_channels.append(self.user_channel)
        for channel in self.participating_channels:
            await self.channel_layer.group_add(
                channel,
                self.channel_name
            )

        await self.accept()

    async def disconnect(self, close_code):
        for group in self.participating_channels:
            await self.channel_layer.group_discard(
                group,
                self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data or '{}')

        # Message endpoint
        if data.get('type') == 'message':
            await self.send_message(data=data)

        elif data.get('type') == 'connect_channel':
            await self.connect_channel(data=data)

        elif data.get('type') == 'disconnect_channel':
            await self.connect_channel(data=data, disconnect=True)

    # Send message to WebSocket
    # TODO Check if redundant
    async def chat_message(self, content: dict):
        await self.send(text_data=json.dumps(content))

    @database_sync_to_async
    def get_participating_channels(self):
        return MessageChannelParticipant.objects.filter(user=self.user).values_list('channel_id', flat=True)

    @database_sync_to_async
    def create_message(self, *, user_id: int, channel_id: int, message: str, attachments_id: int, parent_id: int):
        try:
            message = message_create(user_id=user_id, channel_id=channel_id, message=message,
                                     attachments_id=attachments_id, parent_id=parent_id)

        except ValidationError as e:
            return e.detail

        return message

    async def send_message(self, data: dict):
        class MessageInputSerializer(serializers.Serializer):
            channel_id = serializers.IntegerField()
            message = serializers.CharField()
            attachments_id = serializers.IntegerField()
            parent_id = serializers.IntegerField()
            topic_id = serializers.IntegerField(required=False)

        serializer = MessageInputSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        channel_id = data.get('channel_id')

        # Save message to database
        message = await self.create_message(user_id=self.user.id,
                                            **data)

        # Send error message to user if string returned
        if isinstance(message, str):
            await self.channel_layer.group_send(
                self.user_channel,
                dict(channel_id=channel_id,
                     type="error",
                     message=message))

            return False

        # Send message to room group
        data['type'] = 'message'

        await self.channel_layer.group_send(
            channel_id,
            data
        )

        return True

    async def connect_channel(self, data, disconnect=False):
        class ConnectChannelInputSerializer(serializers.Serializer):
            channel_id = serializers.IntegerField()

        serializer = ConnectChannelInputSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        channel_id = data.get('channel_id')

        if not disconnect and channel_id in await self.get_participating_channels():
            await self.channel_layer.group_add(channel_id, self.channel_name)
            self.participating_channels.append(channel_id)

        elif disconnect and channel_id in self.participating_channels:
            await self.channel_layer.group_discard(channel_id, self.channel_name)

        else:
            await self.channel_layer.group_send(self.user_channel,
                                                dict(channel_id=channel_id,
                                                     type="error",
                                                     message="Unknown operation"))

        return True
