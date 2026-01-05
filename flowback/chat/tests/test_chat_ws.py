from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework.authtoken.models import Token
from rest_framework.test import APITransactionTestCase

from backend.middleware import TokenAuthMiddleware
from flowback.chat.consumers import ChatConsumer
from flowback.chat.tests.factories import MessageChannelFactory, MessageChannelParticipantFactory
from flowback.group.models import GroupUser
from flowback.group.tests.factories import GroupFactory, GroupUserFactory
from flowback.user.models import User
from flowback.user.services import user_get_chat_channel
from flowback.user.tests.factories import UserFactory


class TestChatWebsocket(APITransactionTestCase):
    def setUp(self):
        self.user_one = UserFactory()
        self.user_two = UserFactory()
        self.user_three = UserFactory()
        self.user_four = UserFactory()

        self.message_channel = MessageChannelFactory(origin_name='user')
        MessageChannelParticipantFactory(channel=self.message_channel, user=self.user_one)
        MessageChannelParticipantFactory(channel=self.message_channel, user=self.user_two)

        self.group = GroupFactory(created_by=self.user_one)
        self.group_message_channel = self.group.chat
        self.group_user_one = GroupUser.objects.get(group=self.group, user=self.user_one)
        self.group_user_two = GroupUserFactory(group=self.group, user=self.user_two)
        self.group_user_three = GroupUserFactory(group=self.group, user=self.user_three)

    async def connect(self, user: User | UserFactory) -> WebsocketCommunicator:
        """
        Communicates with the websocket
        Remember to disconnect using communicator.disconnect()
        :return: WebsocketCommunicator
        """
        user_one_token, created = await Token.objects.aget_or_create(user=user)
        application = TokenAuthMiddleware(ChatConsumer.as_asgi())
        communicator = WebsocketCommunicator(application, f"/chat/ws?token={user_one_token.key}")
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        return communicator

    async def test_connect(self):
        communicator = await self.connect(user=self.user_one)
        communicator_two = await self.connect(user=self.user_two)
        await communicator.disconnect()
        await communicator_two.disconnect()

    async def test_send_message_user(self):
        communicator_one = await self.connect(user=self.user_one)
        communicator_two = await self.connect(user=self.user_two)

        # Message
        message = dict(channel_id=self.message_channel.id, message="test message", method="message_create")
        await communicator_one.send_json_to(message)

        # Check if the user got a confirmation
        response = await communicator_one.receive_json_from(timeout=5)
        self.assertNotEqual(response.get('status'), 'error', response)

        # Check if the recipient got the message
        response = await communicator_two.receive_json_from(timeout=5)
        self.assertTrue(response.get('user'))
        self.assertEqual(response['user'].get('username'), self.user_one.username)
        self.assertEqual(response['user'].get('id'), self.user_one.id)
        self.assertEqual(response.get('message'), message.get('message'))

        # Message back
        message = dict(channel_id=self.message_channel.id, message="test message two", method="message_create")
        await communicator_two.send_json_to(message)

        # Check if the user got a confirmation
        response = await communicator_two.receive_json_from(timeout=5)
        self.assertNotEqual(response.get('status'), 'error', response)

        # Check if the recipient got the message
        response = await communicator_one.receive_json_from(timeout=5)
        self.assertTrue(response.get('user'))
        self.assertEqual(response['user'].get('username'), self.user_two.username)
        self.assertEqual(response['user'].get('id'), self.user_two.id)
        self.assertEqual(response.get('message'), message.get('message'))

        await communicator_one.disconnect()
        await communicator_two.disconnect()

    async def test_send_message_new_user(self):
        communicator_one = await self.connect(user=self.user_one)
        communicator_two = await self.connect(user=self.user_two)
        communicator_three = await self.connect(user=self.user_three)
        communication_four = await self.connect(user=self.user_four)

        channel_factory = sync_to_async(MessageChannelFactory)
        participant_factory = sync_to_async(MessageChannelParticipantFactory)

        channel = await channel_factory(origin_name='user')
        await participant_factory(channel=channel, user=self.user_one)
        await participant_factory(channel=channel, user=self.user_three)

        message = dict(channel_id=channel.id, message="test message", method="message_create")
        await communicator_one.send_json_to(message)

        await communicator_three.receive_json_from(timeout=5)

        await communicator_one.disconnect()
        await communicator_two.disconnect()
        await communicator_three.disconnect()
        await communication_four.disconnect()

    async def test_send_message_user_get_chat_channel(self):
        communicator_one = await self.connect(user=self.user_three)
        communicator_two = await self.connect(user=self.user_four)

        ugcc = sync_to_async(user_get_chat_channel)

        chat_channel = await ugcc(fetched_by=self.user_three, target_user_ids=[self.user_four.id])

        await communicator_one.receive_json_from(timeout=5)

        await communicator_one.disconnect()
        await communicator_two.disconnect()

    async def test_send_message_group(self):
        def message_check(data):
            self.assertNotEqual(data.get('status'), 'error', data)
            self.assertEqual(data.get('message'), message.get('message'))
            self.assertEqual(data.get('channel_id'), message.get('channel_id'))
            self.assertTrue(data.get('user'))
            self.assertEqual(data['user'].get('username'), self.user_one.username)

        communicator_one = await self.connect(user=self.user_one)
        communicator_two = await self.connect(user=self.user_two)
        communicator_three = await self.connect(user=self.user_three)
        communicator_four = await self.connect(user=self.user_four)

        # Message
        message = dict(channel_id=self.group_message_channel.id, message="test message", method="message_create")
        await communicator_one.send_json_to(message)

        response = await communicator_one.receive_json_from(timeout=5)
        message_check(response)

        response = await communicator_two.receive_json_from(timeout=5)
        message_check(response)

        response = await communicator_three.receive_json_from(timeout=5)
        message_check(response)

        with self.assertRaises(TimeoutError):
            await communicator_four.receive_json_from(timeout=1)

        await communicator_one.disconnect()
        await communicator_two.disconnect()
        await communicator_three.disconnect()
