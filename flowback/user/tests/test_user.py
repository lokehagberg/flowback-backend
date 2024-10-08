import json

from rest_framework import status
from rest_framework.test import APITransactionTestCase, APIRequestFactory, force_authenticate

from flowback.chat.models import MessageChannel, MessageChannelParticipant
from flowback.chat.tests.factories import MessageChannelFactory
from flowback.common.tests import generate_request
from flowback.user.tests.factories import UserFactory
from flowback.user.views.user import UserDeleteAPI, UserGetChatChannelAPI


class UserTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        (self.user_one,
         self.user_two,
         self.user_three) = (UserFactory() for x in range(3))

    def test_user_delete(self):
        user = self.user_one

        factory = APIRequestFactory()
        view = UserDeleteAPI.as_view()
        request = factory.post('')
        force_authenticate(request, user=user)
        view(request)

        user.refresh_from_db()
        self.assertTrue(user.username.startswith('deleted_user'))
        self.assertTrue(user.email.startswith('deleted_user'))

        self.assertTrue(not all([user.is_active,
                                 user.email_notifications,
                                 user.profile_image,
                                 user.banner_image,
                                 user.bio,
                                 user.website,
                                 user.kanban,
                                 user.schedule]))

    def test_user_get_chat_channel(self):
        participants = UserFactory.create_batch(25)

        response = generate_request(api=UserGetChatChannelAPI,
                                    data=dict(target_user_ids=[u.id for u in participants]),
                                    user=self.user_one)

        # Run second time to make sure we get the same channel_id
        response_two = generate_request(api=UserGetChatChannelAPI,
                                        data=dict(target_user_ids=[u.id for u in participants]),
                                        user=self.user_one)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response_two.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(response.data['id'], response_two.data['id'])
        self.assertTrue(MessageChannel.objects.filter(id=response.data['id']).exists())

        # Count all participants + the user itself
        self.assertEqual(MessageChannelParticipant.objects.filter(channel_id=response.data['id']).count(), 26)
