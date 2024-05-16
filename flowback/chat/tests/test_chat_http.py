import random
from pprint import pprint

from django.test import TransactionTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ..models import (MessageChannel,
                      Message,
                      MessageChannelParticipant,
                      MessageChannelTopic,
                      MessageFileCollection)

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
from ..views import MessageListAPI, MessageChannelPreviewAPI,GetAllParentsOfCommentAPI,GetAllChildsOfCommentAPI
from ...user.tests.factories import UserFactory


# Create your tests here.


class ChatTestHTTP(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user_one = UserFactory()
        self.user_two = UserFactory()
        self.message_channel = MessageChannelFactory()
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
        # Direct message channel
        channel = self.message_channel
        channel_participant_one = self.message_channel_participant_one
        channel_participant_two = self.message_channel_participant_two
        [MessageFactory(user=channel_participant_one.user, channel=channel) for x in range(10)]
        [MessageFactory(user=channel_participant_two.user, channel=channel) for x in range(10)]

        # User left this channel
        [MessageFactory(user=channel_participant_one.user) for x in range(10)]

        # Direct message channel two
        channel_two = MessageChannelFactory()
        channel_two_participant_one = MessageChannelParticipantFactory(channel=channel_two,
                                                                       user=channel_participant_one.user)
        channel_two_participant_two = MessageChannelParticipantFactory(channel=channel_two,
                                                                       user=channel_participant_two.user)
        [MessageFactory(user=channel_two_participant_two.user,
                        channel=channel_two) for x in range(10)]
        [MessageFactory(user=channel_two_participant_one.user,
                        channel=channel_two) for x in range(10)]

        factory = APIRequestFactory()
        request = factory.get('')
        view = MessageChannelPreviewAPI.as_view()
        force_authenticate(request, user=channel_participant_one.user)
        response = view(request)

        self.assertEqual(response.data.get('count'), 2)

    def test_parent_comment_fetch(self):
        channel = self.message_channel
        channel_participant_one = self.message_channel_participant_one

        root = MessageFactory(user=channel_participant_one.user, channel=channel)
        first_level = [MessageFactory(user=channel_participant_one.user, channel=channel, parent_id=root.id).id for x in range(3)]
        second_level = [MessageFactory(user=channel_participant_one.user, channel=channel, parent_id=first_level[0]) for x in range(10)]

        child_node = second_level[0]
        query_params = {
            "channel_id":channel.id,
            "comment_id":child_node.id
        }   
        factory = APIRequestFactory()
        request = factory.get('', data=query_params)
        view = GetAllParentsOfCommentAPI.as_view()
        force_authenticate(request, user=channel_participant_one.user)
        response = view(request)
        comment_ids = [each.get('id') for each in response.data.get('results')]


        self.assertEqual(response.status_code,200)
        self.assertEqual(comment_ids,[root.id,first_level[0],child_node.id])
        
    def test_child_comment_fetch(self):
        channel = self.message_channel
        channel_participant_one = self.message_channel_participant_one
        
        root = MessageFactory(user=channel_participant_one.user, channel=channel)
        first_level = [MessageFactory(user=channel_participant_one.user, channel=channel, parent_id=root.id) for x in range(3)]
        second_level = [MessageFactory(user=channel_participant_one.user, channel=channel, parent_id=first_level[0].id).id for x in range(5)]

        
        query_params = {
            "channel_id":channel.id,
            "comment_id":first_level[0].id
        }

        factory = APIRequestFactory()
        request = factory.get('', data=query_params)
        view = GetAllChildsOfCommentAPI.as_view()
        force_authenticate(request, user=channel_participant_one.user)
        response = view(request)
        comment_ids = [each.get('id') for each in response.data.get('results')]


        self.assertEqual(response.status_code,200)
        self.assertEqual(comment_ids,[first_level[0].id,*second_level])

    def test_child_of_leaf_node(self):
        channel = self.message_channel
        channel_participant_one = self.message_channel_participant_one

        root = MessageFactory(user=channel_participant_one.user, channel=channel)
        first_level = [MessageFactory(user=channel_participant_one.user, channel=channel, parent_id=root.id) for x in range(3)]

        query_params = {
            "channel_id":channel.id,
            "comment_id":first_level[0].id
        }

        factory = APIRequestFactory()
        request = factory.get('', data=query_params)
        view = GetAllChildsOfCommentAPI.as_view()
        force_authenticate(request, user=channel_participant_one.user)
        response = view(request)


        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data.get('count'),1)

    def test_parent_of_root_node(self):
        channel = self.message_channel
        channel_participant_one = self.message_channel_participant_one

        root = MessageFactory(user=channel_participant_one.user, channel=channel)
        first_level = [MessageFactory(user=channel_participant_one.user, channel=channel, parent_id=root.id) for x in range(3)]

        query_params = {
            "channel_id":channel.id,
            "comment_id":root.id
        }

        factory = APIRequestFactory()
        request = factory.get('', data=query_params)
        view = GetAllParentsOfCommentAPI.as_view()
        force_authenticate(request, user=channel_participant_one.user)
        response = view(request)


        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data.get('count'),1)

'''
Above mentioned test cases will check the following the Scenario's:
  - For a given comment ID, fetching all parents in their respective chronological order.
  - For a given comment ID, fetching all children in their respective chronological order.
  - For a given comment ID, getting only its children, not siblings.
  - For a given comment ID of root node, not getting any parent data.
  - For a given comment ID of leaf node, not getting and child data

'''