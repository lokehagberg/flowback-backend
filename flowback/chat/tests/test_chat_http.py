from pprint import pprint

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase

from ..models import (MessageChannel,
                      MessageChannelParticipant)

from ..services import (message_create,
                        message_update,
                        message_delete,
                        message_channel_create,
                        message_channel_delete,
                        message_channel_join,
                        message_channel_leave)

from .factories import (MessageChannelFactory,
                        MessageFactory,
                        MessageChannelParticipantFactory,
                        MessageChannelTopicFactory,
                        MessageFileCollectionFactory)
from ..views import MessageListAPI, MessageChannelPreviewAPI, MessageChannelParticipantListAPI
from ...common.tests import generate_request
from ...user.tests.factories import UserFactory


# Create your tests here.


class ChatTestHTTP(APITestCase):
    def setUp(self):
        self.user_one = UserFactory()
        self.user_two = UserFactory()
        self.message_channel = MessageChannelFactory()
        self.message_channel_participant_three = MessageChannelParticipantFactory(channel=self.message_channel)
        self.message_channel_participant_one = MessageChannelParticipantFactory(channel=self.message_channel)
        self.message_channel_participant_two = MessageChannelParticipantFactory(channel=self.message_channel)
        self.message_channel_topic = MessageChannelTopicFactory(channel=self.message_channel)
        self.message_channel_file_collection = MessageFileCollectionFactory(channel=self.message_channel)

    def test_message_channel_create(self):
        channel = message_channel_create(origin_name="user", title="test")

        self.assertTrue(channel.id)

    def test_message_channel_delete(self):
        channel_id = self.message_channel.id
        message_channel_delete(channel_id=channel_id)

        self.assertFalse(MessageChannel.objects.filter(id=channel_id).exists())

    def test_message_channel_join(self):
        participant = message_channel_join(user_id=self.user_one.id, channel_id=self.message_channel.id)

        self.assertTrue(participant.id)
        self.assertTrue(isinstance(participant, MessageChannelParticipant))

    def test_message_channel_leave(self):
        participant_id = self.message_channel_participant_one.id
        message_channel_leave(user_id=self.message_channel_participant_one.user.id, channel_id=self.message_channel.id)

        self.assertFalse(MessageChannelParticipant.objects.filter(id=participant_id).exists())

    def test_message_create(self):
        message_one = message_create(user_id=self.message_channel_participant_one.user.id,
                                     channel_id=self.message_channel.id,
                                     message="test message",
                                     attachments_id=self.message_channel_file_collection.id)

        self.assertTrue(message_one.id)
        self.assertEqual(message_one.message, "test message")
        self.assertEqual(message_one.user.id, self.message_channel_participant_one.user.id)
        self.assertEqual(message_one.attachments_id, self.message_channel_file_collection.id)

    def test_message_update(self):
        message = MessageFactory()

        message_update(user_id=message.user_id, message_id=message.id, message="testify message")

        message.refresh_from_db()
        self.assertEqual(message.message, "testify message")

    def test_message_delete(self):
        message = MessageFactory()
        message_delete(user_id=message.user_id, message_id=message.id)
        message.refresh_from_db()

        self.assertFalse(message.active)

    def test_message_list(self):
        [MessageFactory(user=self.message_channel_participant_one.user,
                        channel=self.message_channel) for x in range(10)]
        [MessageFactory(user=self.message_channel_participant_one.user) for x in range(10)]  # User left channel

        factory = APIRequestFactory()
        view = MessageListAPI.as_view()
        request = factory.get('')

        user = self.message_channel_participant_one.user
        force_authenticate(request, user=user)
        response = view(request, channel_id=self.message_channel.id)

        self.assertEqual(response.data.get('count'), 10)

    def test_message_channel_preview(self):
        # Test if there's correct amount of messages
        for i in range(10):
            channel = MessageChannelFactory(origin_name='user')
            channel_participant_one = MessageChannelParticipantFactory(
                channel=channel,
                user=self.message_channel_participant_one.user,
                timestamp=timezone.now())
            channel_participant_two = MessageChannelParticipantFactory(
                channel=channel,
                user=self.message_channel_participant_two.user,
                timestamp=timezone.now())

            [MessageFactory(user=channel_participant_one.user, channel=channel) for x in range(10)]
            [MessageFactory(user=channel_participant_two.user, channel=channel) for x in range(10)]
            [MessageFactory(user=channel_participant_one.user, channel=channel) for x in range(10)]

            channel_two = MessageChannelFactory(origin_name='user')
            channel_participant_one_one = MessageChannelParticipantFactory(
                channel=channel_two,
                user=self.message_channel_participant_one.user)
            channel_participant_one_two = MessageChannelParticipantFactory(
                channel=channel_two,
                user=self.message_channel_participant_two.user)
            channel_participant_one_three = MessageChannelParticipantFactory(
                channel=channel_two,
                user=self.message_channel_participant_three.user)

            [MessageFactory(user=channel_participant_one_one.user, channel=channel_two) for x in range(10)]
            [MessageFactory(user=channel_participant_one_two.user, channel=channel_two) for x in range(10)]
            [MessageFactory(user=channel_participant_one_one.user, channel=channel_two) for x in range(10)]

            factory = APIRequestFactory()
            request = factory.get('', data=dict(order_by='created_at_desc'))
            request_two = factory.get('', data=dict(order_by='created_at_desc', origin_name='user'))
            request_three = factory.get('', data=dict(order_by='created_at_desc', origin_name='group'))
            view = MessageChannelPreviewAPI.as_view()

            # Check if all channels are shown
            force_authenticate(request, user=channel_participant_one.user)
            response = view(request)

            if i > 0:
                self.assertEqual(response.data.get('count'), 3 + i * 2, response.data)
                self.assertTrue(response.data['results'][i]['timestamp'])
                self.assertEqual(response.data['results'][(2 * i) + 1]['participants'], 2,
                                 [(i['created_at'], i['participants']) for i in response.data['results']])
                self.assertGreater(response.data['results'][i - 1]['created_at'],
                                   response.data['results'][i]['created_at'])

            # Check if one channel is shown
            force_authenticate(request_two, user=channel_participant_one.user)
            response = view(request_two)

            if i > 0:
                self.assertEqual(response.data.get('count'), 2 + i * 2)
                self.assertTrue(response.data['results'][i]['timestamp'])
                self.assertEqual(response.data['results'][2 * (i - 1)]['participants'], 3,
                                 [(i['created_at'], i['participants']) for i in response.data['results']])
                self.assertGreater(response.data['results'][i - 1]['created_at'],
                                   response.data['results'][i]['created_at'])

            force_authenticate(request_three, user=channel_participant_one.user)
            response = view(request_three)

            if i > 0:
                self.assertEqual(response.data.get('count'), 0)

    def test_message_channel_participant(self):
        channel = MessageChannelFactory()
        channel_participants = MessageChannelParticipantFactory.create_batch(50, channel=channel)

        # Test if success
        response = generate_request(MessageChannelParticipantListAPI,
                                    url_params=dict(channel_id=channel.id),
                                    user=channel_participants[0].user)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data.get('count'), 50)

        # Test permission denied
        response = generate_request(MessageChannelParticipantListAPI,
                                    url_params=dict(channel_id=channel.id),
                                    user=self.user_one)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
