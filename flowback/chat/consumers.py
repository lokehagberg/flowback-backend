import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from flowback.common.services import get_object
from flowback.user.models import User
from flowback.group.models import Group
from flowback.group.services import group_user_permissions
from flowback.chat.models import GroupMessage, DirectMessage


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.group_id = self.scope['url_route']['kwargs'].get('group')
        self.chat_id = f'group_{self.group_id}'

        if self.scope['user'].is_anonymous or not self.group_id:
            await self.close()

        self.group = await self.group_channel_connect()

        # Join room group
        await self.channel_layer.group_add(
            self.chat_id,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.chat_id,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data = json.loads(text_data)
        message = text_data['message']

        class OutputSerializer(serializers.ModelSerializer):
            class Meta:
                model = User
                fields = 'id', 'username', 'profile_image'

        await self.group_channel_message(message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.chat_id,
            {
                'type': 'chat_message',
                'user': OutputSerializer(self.user).data,
                'message': message
            }
        )

    # Receive message from room group
    async def chat_message(self, content: dict):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': content.get('message'),
            'user': content.get('user')
        }))

    @database_sync_to_async
    def group_channel_connect(self):
        group = get_object_or_404(Group, pk=self.group_id)
        group_user_permissions(user=self.user.id,
                               group=self.group_id)

        return group

    @database_sync_to_async
    def group_channel_message(self, message):
        group_user = group_user_permissions(group=self.group_id, user=self.user.id)
        obj = GroupMessage(group_user=group_user,
                           message=message)

        obj.full_clean()
        obj.save()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']

        if self.scope['user'].is_anonymous:
            await self.close()

        # chat_id: user_<id:int>

        user_groups = Group.objects.filter(groupuser__user__in=self.user).all()
        self.chat_groups = [f'group_{x.id}' for x in user_groups] + [f'user_{self.user.id}']

        # Join room group
        for group in self.chat_groups:
            await self.channel_layer.group_add(
                group,
                self.channel_name
            )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        for group in self.chat_groups:
            await self.channel_layer.group_discard(
                group,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        class FilterSerializer(serializers.Serializer):
            target_type = serializers.ChoiceField(('group', 'direct'))
            message = serializers.CharField()
            target = serializers.IntegerField()

        class OutputSerializer(serializers.ModelSerializer):
            class Meta:
                model = User
                fields = 'id', 'username', 'profile_image'

        serializer = FilterSerializer(data=json.loads(text_data or '{}'))
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Save message to database
        if data.get('target_type') == 'direct':
            await self.direct_message(**data)

        else:
            await self.group_message(**data)

        # Send message to room group
        await self.channel_layer.group_send(
            await self.get_message_target(**data),
            {
                'type': 'chat_message',
                'target_type': data.get('target_type'),
                'user': OutputSerializer(self.user).data,
                'message': data.get('message'),
            }
        )

    # Receive message from room group
    async def chat_message(self, content: dict):

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': content.get('message'),
            'user': content.get('user')
        }))

    @database_sync_to_async
    def get_message_target(self, target: int, target_type: str):
        return f'user_{target}' if target_type == 'direct' else f'group_{target}'

    @database_sync_to_async
    def direct_message(self, *, message: str, target: int):
        target = get_object(User, pk=target)

        obj = DirectMessage(user=self.user,
                            target_id=target.id,
                            message=message)

        obj.full_clean()
        obj.save()

    @database_sync_to_async
    def group_message(self, message: str, target: int):
        group_user = group_user_permissions(group=target, user=self.user.id)
        obj = GroupMessage(group_user=group_user,
                           message=message)

        obj.full_clean()
        obj.save()



class DirectChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']

        if self.scope['user'].is_anonymous:
            await self.close()

        # chat_id: user_<id:int>
        self.group_name = f'user_{self.user.id}'

        # Join room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        class FilterSerializer(serializers.Serializer):
            message = serializers.CharField()
            target = serializers.IntegerField()

        class OutputSerializer(serializers.ModelSerializer):
            class Meta:
                model = User
                fields = 'id', 'username', 'profile_image'

        serializer = FilterSerializer(data=json.loads(text_data or '{}'))
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        await self.direct_message(**data)

        # Send message to room group
        await self.channel_layer.group_send(
            await self.get_message_target(data.get('target')),
            {
                'type': 'chat_message',
                'user': OutputSerializer(self.user).data,
                'message': data.get('message'),
            }
        )

    # Receive message from room group
    async def chat_message(self, content: dict):

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': content.get('message'),
            'user': content.get('user')
        }))

    @database_sync_to_async
    def get_message_target(self, target: int):
        get_object(User, pk=target)

        return f'user_{target}'

    @database_sync_to_async
    def direct_message(self, *, message: str, target: int):
        obj = DirectMessage(user=self.user,
                            target_id=target,
                            message=message)

        obj.full_clean()
        obj.save()

