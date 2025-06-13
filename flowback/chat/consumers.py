import json
from json import JSONDecodeError
from typing import Union

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from flowback.chat.models import MessageChannelParticipant
from flowback.chat.serializers import MessageSerializer
from flowback.chat.services import message_create, message_update, message_delete


class ChatConsumer(AsyncWebsocketConsumer):

    # The function responsible for establishing connections between the end user and the server
    async def connect(self):
        self.user = self.scope['user']

        if self.scope['user'].is_anonymous:
            return await self.close()

        # Assign user to their channels
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

        # Disconnect from channels
        for channel in self.participating_channels:
            await self.channel_layer.group_discard(
                f"{channel}",
                self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            data = json.loads(text_data or '{}')

        except JSONDecodeError as e:
            return await self.send_error_message(method="JSONDecodeError",
                                                 detail="Wrong Format")

        # Message endpoints
        if data.get('method') == 'message_create':
            await self.message_create(data=data)

        elif data.get('method') == 'message_update':
            await self.message_update(data=data)

        elif data.get('method') == 'message_delete':
            await self.message_delete(data=data)

        elif data.get('method') == 'message_notify':
            await self.message_notify(data=data)

        elif data.get('method') == 'connect_channel':
            await self.connect_channel(data=data)

        elif data.get('method') == 'disconnect_channel':
            await self.connect_channel(data=data, disconnect=True)

        elif method := data.get('method'):
            return await self.send_error_message(method="UnknownMethod",
                                                 detail=f"Unknown 'method' key in request (got '{method}')")

        elif data.get('method') is None:
            return await self.send_error_message(method="MissingMethod",
                                                 detail="Missing 'method' key in request")

        return True

    # Messages passes here before being sent
    async def message(self, content: dict):
        await self.send(text_data=json.dumps(content))

    @database_sync_to_async
    def get_participating_channels(self):
        return list(MessageChannelParticipant.objects.filter(user=self.user,
                                                             active=True).values_list('channel_id',
                                                                                      flat=True))

    @staticmethod
    def generate_status_message(message: str, method: str = None, **kwargs):
        return dict(type="message",
                    method=method,
                    message=message,
                    **kwargs)

    # Validation for message, additionally sends an error to the user if it fails
    async def validate_serializer(self, *, serializer, method: str, data: dict) -> Union[dict, bool]:
        try:
            serializer = serializer(data=data)
            serializer.is_valid(raise_exception=True)
            return serializer.validated_data

        except ValidationError as e:
            message = self.generate_status_message(message_id=data.get('message_id'),
                                                   message=json.dumps(e.detail),
                                                   method=method,
                                                   status="error")

            await self.send_message(channel_id=self.user_channel, message=message)
            return False

    async def send_error_message(self, *, detail: Union[dict, str], method: str, **extra) -> None:
        message = self.generate_status_message(message=json.dumps(detail) if isinstance(detail, dict) else detail,
                                               message_is_json=True if isinstance(detail, dict) else False,
                                               method=method,
                                               status="error",
                                               **extra)

        await self.send_message(channel_id=self.user_channel, message=message)

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
        class InputSerializer(serializers.Serializer):
            channel_id = serializers.IntegerField()
            message = serializers.CharField()
            attachments_id = serializers.IntegerField(required=False)
            parent_id = serializers.IntegerField(required=False)
            topic_id = serializers.IntegerField(required=False)

        serializer = InputSerializer(data=data)

        try:
            serializer.is_valid(raise_exception=True)
            message = await self._create_message(user_id=self.user.id, **serializer.validated_data)

        except ValidationError as e:
            return await self.send_error_message(detail=e.detail,
                                                 method="message_create",
                                                 channel_id=self.user_channel)

        await self.send_message(channel_id=data.get('channel_id'), message=message)

    @database_sync_to_async
    def _update_message(self, *,
                        user_id: int,
                        message_id: int,
                        **data):

        update = message_update(user_id=user_id, message_id=message_id, **data)

        return dict(**MessageSerializer(update[0]).data, method="message_update")

    async def message_update(self, data: dict):
        class InputSerializer(serializers.Serializer):
            message_id = serializers.IntegerField()
            message = serializers.CharField()

        serializer = InputSerializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
            message = await self._update_message(user_id=self.user.id, **serializer.validated_data)

        except ValidationError as e:
            return await self.send_error_message(detail=e.detail,
                                                 method="message_update",
                                                 channel_id=self.user_channel)

        await self.send_message(channel_id=message['channel_id'], message=message)

    @database_sync_to_async
    def _delete_message(self, *,
                        user_id: int,
                        message_id: int):
        message = message_delete(user_id=user_id, message_id=message_id)
        return dict(**MessageSerializer(message).data, method="message_delete")

    async def message_delete(self, data: dict):
        class InputSerializer(serializers.Serializer):
            message_id = serializers.IntegerField()

        serializer = InputSerializer(data=data)

        try:
            serializer.is_valid(raise_exception=True)
            message = await self._delete_message(user_id=self.user.id, **serializer.validated_data)

        except ValidationError as e:
            return await self.send_error_message(detail=e.detail,
                                                 method="message_delete",
                                                 channel_id=self.user_channel)

        await self.send_message(channel_id=message['channel_id'], message=message)

    # Function to notify e.g. if the user is typing
    async def message_notify(self, data: dict):
        class InputSerializer(serializers.Serializer):
            channel_id = serializers.IntegerField()
            action = serializers.ChoiceField(choices=['is_typing'])

        serializer = InputSerializer(data=data)

        try:
            serializer.is_valid(raise_exception=True)
            await MessageChannelParticipant.objects.aget(user=self.user,
                                                         channel_id=data['channel_id'])

        except ValidationError as e:
            return await self.send_error_message(detail=e.detail,
                                                 method="message_notify",
                                                 channel_id=self.user_channel)

        except MessageChannelParticipant.DoesNotExist:
            return await self.send_error_message(detail="User is not participating in this channel",
                                                 method="message_notify",
                                                 channel_id=self.user_channel)

        data = serializer.validated_data
        message = self.generate_status_message(channel_id=data['channel_id'],
                                               user_id=self.user.id,
                                               message=data['action'],
                                               method='message_notify')

        await self.send_message(channel_id=str(data['channel_id']), message=message)

    # Allows user to add/remove channels without reconnecting, for e.g. joining and leaving a group
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
