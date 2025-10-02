import json
import math

from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from flowback.chat.models import MessageChannel, MessageChannelParticipant
from flowback.chat.tests.factories import MessageChannelFactory
from flowback.comment.tests.factories import CommentFactory
from flowback.common.tests import generate_request
from flowback.group.models import GroupThread, GroupUser
from flowback.group.tests.factories import GroupThreadFactory, GroupUserFactory, GroupFactory, WorkGroupFactory, \
    WorkGroupUserFactory
from flowback.notification.models import NotificationObject, Notification, NotificationSubscription, NotificationChannel
from flowback.poll.models import Poll
from flowback.poll.tests.factories import PollFactory
from flowback.user.models import User, UserChatInvite
from flowback.user.services import user_create, user_create_verify, user_delete
from flowback.user.tests.factories import UserFactory
from flowback.user.views.home import UserHomeFeedAPI
from flowback.user.views.user import UserDeleteAPI, UserGetChatChannelAPI, UserUpdateApi, UserChatInviteAPI, UserGetApi, \
    UserNotificationSubscribeAPI, UserCreateApi
from flowback.user.models import OnboardUser


class UserTest(APITestCase):
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

    def test_user_create(self):
        for i in range(3):
            user_create(email="test@example.com")
            generate_request(UserCreateApi, data=dict(email="test@example.com"))
            onboard_user = user_create(email="test@example.com")  # Test twice for unique conflicts


            print(onboard_user.verification_code, OnboardUser.objects.get(id=onboard_user.id).verification_code)

            user = user_create_verify(username="test_user",
                                      verification_code=str(onboard_user.verification_code),
                                      password="TestPassword!=27")

            self.assertTrue(User.objects.filter(id=user.id).exists())

            user_delete(user_id=user.id)  # Test if user can create new account after deletion

    def test_user_create_api_with_existing_onboard_user(self):
        """Test UserCreateApi when an OnboardUser with the same email already exists"""
        test_email = "duplicate@example.com"
        
        # First, create an OnboardUser directly
        OnboardUser.objects.create(email=test_email)
        self.assertTrue(OnboardUser.objects.filter(email=test_email).exists())
        
        # Then create another user with the same email through the API
        response = generate_request(UserCreateApi, data=dict(email=test_email))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify that the one OnboardUser exists
        onboard_users = OnboardUser.objects.filter(email=test_email)
        self.assertEqual(onboard_users.count(), 1)

    def test_user_create_api_with_existing_user_email(self):
        """Test UserCreateApi when a User with the same email already exists"""
        test_email = "existing_user@example.com"
        
        # Create a full User
        UserFactory(email=test_email)
        
        # Then create an OnboardUser with the same email through the API
        response = generate_request(UserCreateApi, data=dict(email=test_email))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify no OnboardUser was created
        self.assertFalse(OnboardUser.objects.filter(email=test_email).exists())

    def test_user_update(self):
        user = UserFactory()
        generate_request(UserUpdateApi,
                         data={"contact_phone": "+46701234567"},
                         user=user)

        self.assertEqual(User.objects.get(id=user.id).contact_phone, "+46701234567")

    def test_user_get(self):
        user = UserFactory(public_status=User.PublicStatus.PRIVATE,
                           dark_theme=True)
        user_two = UserFactory(public_status=User.PublicStatus.PUBLIC,
                               bio='test_bio',
                               dark_theme=True)
        user_three = UserFactory(public_status=User.PublicStatus.GROUP_ONLY,
                                 bio='test_bio',
                                 dark_theme=True)

        group = GroupFactory(created_by=user_three)
        GroupUserFactory(group=group, user=user_two)
        GroupUserFactory(group=group, user=user)

        response = generate_request(UserGetApi, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['dark_theme'], True)

        response = generate_request(UserGetApi, user=user, data=dict(user_id=user_two.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotIn('dark_theme', response.data.keys())
        self.assertIn('bio', response.data.keys())

        response = generate_request(UserGetApi, user=user, data=dict(user_id=user_three.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotIn('dark_theme', response.data.keys())
        self.assertIn('bio', response.data.keys())

        response = generate_request(UserGetApi, user=user_three, data=dict(user_id=user.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotIn('dark_theme', response.data.keys())
        self.assertNotIn('bio', response.data.keys())
        self.assertIn('username', response.data.keys())


    def test_user_home_feed_order(self):
        group_user, group_user_three = GroupUserFactory.create_batch(size=2, group__public=False)
        group_user_two = GroupUserFactory(group__public=True)

        # TODO Test with workgroup

        GroupThreadFactory.create_batch(size=2)
        polls = PollFactory.create_batch(size=5, created_by=group_user)
        polls[1].pinned = True
        polls[1].save()

        PollFactory.create_batch(size=5, created_by=group_user_two, public=True)
        GroupThreadFactory.create_batch(size=5, created_by=group_user_two, public=True)

        polls = PollFactory.create_batch(size=5, created_by=group_user_three)
        poll_with_comments = polls[0] # Testing total comments aggregate
        CommentFactory.create_batch(size=5,
                                    author=group_user_three.user,
                                    comment_section=poll_with_comments.comment_section)

        GroupThreadFactory.create_batch(size=5, created_by=group_user_three)

        response = generate_request(api=UserHomeFeedAPI, user=group_user.user)

        response_pinned_test = generate_request(api=UserHomeFeedAPI,
                                                user=group_user.user,
                                                data=dict(order_by='pinned,created_at_desc'))

        self.assertEqual(response_pinned_test.data['count'], response.data['count'])
        self.assertEqual(response_pinned_test.data['results'][0]['pinned'], True)

        # Check if order_by is for created_at, in descending order
        for x in range(1, response.data['count']):
            self.assertTrue(response.data['results'][x]['created_at'] < response.data['results'][x - 1]['created_at'])

            if response.data['results'][x]['related_model'] == "poll":
                self.assertTrue(Poll.objects.filter(created_by__group=response.data['results'][x]['group_id'],
                                                    id=response.data['results'][x]['id']).exists())

            if response.data['results'][x]['related_model'] == "thread":
                self.assertTrue(GroupThread.objects.filter(created_by__group=response.data['results'][x]['group_id'],
                                                    id=response.data['results'][x]['id']).exists())

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 15)

    def test_user_home_feed_visibility(self):
        # Create public group with 5 polls and 10 threads
        group_public = GroupFactory(public=True)
        group_user_public_workgroupuser = WorkGroupUserFactory(work_group__group=group_public,
                                                               group_user__group=group_public)
        group_public_workgroup = group_user_public_workgroupuser.work_group
        group_user_public_admin = GroupUser.objects.get(user=group_public.created_by)
        group_user_public = GroupUserFactory(group=group_public)
        public_threads = GroupThreadFactory.create_batch(size=5, created_by=group_user_public, public=True)
        public_polls = PollFactory.create_batch(size=5, created_by=group_user_public, public=True)
        public_threads_workgroup = GroupThreadFactory.create_batch(size=5,
                                                                   created_by=group_user_public,
                                                                   work_group=group_public_workgroup)

        # Create private group with 5 polls and 10 threads
        group_private = GroupFactory(public=False, hide_poll_users=True)
        group_user_private_workgroupuser = WorkGroupUserFactory(work_group__group=group_private,
                                                                group_user__group=group_private)
        group_user_private_workgroup = group_user_private_workgroupuser.work_group
        group_private_workgroup = group_user_private_workgroupuser.work_group
        group_user_private_admin = GroupUser.objects.get(user=group_private.created_by)
        group_user_private = GroupUserFactory(group=group_private)
        private_threads = GroupThreadFactory.create_batch(size=5, created_by=group_user_private, pinned=True)
        private_polls = PollFactory.create_batch(size=5, created_by=group_user_private)
        private_threads_workgroup = GroupThreadFactory.create_batch(size=5,
                                                                    created_by=group_user_private,
                                                                    work_group=group_private_workgroup)

        # Public testing

        ## User
        response = generate_request(api=UserHomeFeedAPI, user=group_user_private.user, data=dict(order_by='pinned,created_at_asc'))
        self.assertTrue(any([i['pinned'] for i in response.data['results']]),
                        [i['pinned'] for i in response.data['results']])  # Placeholder test for pinned
        self.assertTrue(all([i['pinned'] for i in response.data['results'][:4]]),
                        [i['pinned'] for i in response.data['results'][:4]])  # Placeholder test for order_by
        self.assertTrue(all([x['created_by'] is None
                             for x in response.data['results']
                             if x['group_id'] == group_user_private.group.id]),
                        [x['created_by'] is None
                         for x in response.data['results']
                         if x['group_id'] == group_user_private.group.id])  # Placeholder test for hide_poll_users
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 20)

        ## Admin
        response = generate_request(api=UserHomeFeedAPI, user=group_user_private_admin.user)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 25)

        ## WorkGroup User
        response = generate_request(api=UserHomeFeedAPI, user=group_user_private_workgroupuser.group_user.user)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 25)

        # Private testing

        ## User
        response = generate_request(api=UserHomeFeedAPI, user=group_user_public.user)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 10)

        ## Admin
        response = generate_request(api=UserHomeFeedAPI, user=group_user_public_admin.user)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 15)

        ## WorkGroup User
        response = generate_request(api=UserHomeFeedAPI, user=group_user_public_workgroupuser.group_user.user)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 15)



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
        self.assertEqual(MessageChannelParticipant.objects.filter(channel_id=response.data['id'],
                                                                  active=False).count(), 25)
        self.assertEqual(MessageChannelParticipant.objects.filter(channel_id=response.data['id'],
                                                                  active=True).count(), 1)

    def user_get_chat_channel_invite(self, participants: int = 1):
        participants = UserFactory.create_batch(participants)

        if len(participants) <= 0:
            raise Exception("Can't run test with no participants")

        response = generate_request(api=UserGetChatChannelAPI,
                                    data=dict(target_user_ids=[u.id for u in participants]),
                                    user=self.user_one)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        channel_id = response.data['id']
        self.assertEqual(UserChatInvite.objects.all().count(), len(participants))
        self.assertEqual(MessageChannelParticipant.objects.filter(channel_id=channel_id, active=True).count(),
                         1)

        self.assertEqual(MessageChannelParticipant.objects.filter(channel_id=channel_id, active=False).count(),
                         len(participants))

        acceptors = 0
        for i, user in enumerate(participants):
            accept = True if i <= math.floor(len(participants) / 2) else False
            acceptors += int(accept)

            response = generate_request(api=UserChatInviteAPI,
                                        data=dict(invite_id=UserChatInvite.objects.get(user=user).id,
                                                  accept=accept),
                                        user=user)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.assertEqual(MessageChannelParticipant.objects.filter(channel_id=channel_id, active=True).count(),
                         acceptors + 1)

        self.assertEqual(UserChatInvite.objects.filter(rejected=True).count(),
                         len(participants) - acceptors)

        self.assertEqual(UserChatInvite.objects.filter(rejected=False).count(), acceptors)

        self.assertEqual(UserChatInvite.objects.filter(rejected=None).count(), 0)

        response = generate_request(api=UserGetChatChannelAPI,
                                    data=dict(target_user_ids=[u.id for u in participants]),
                                    user=self.user_one)

        self.assertEqual(response.data['id'], channel_id, "Channel ID should not have changed")

        self.assertEqual(UserChatInvite.objects.all().count(), len(participants))
        self.assertEqual(UserChatInvite.objects.filter(rejected=True).count(), 0)

    def test_user_get_chat_channel_invite_duo(self):
        self.user_get_chat_channel_invite(participants=1)

    def test_user_get_chat_channel_invite_group(self):
        self.user_get_chat_channel_invite(participants=25)

    def test_notify_user_chat(self):
        """Test the notify_chat method in the User model"""
        # Create a user and a message channel
        user = UserFactory()
        message_channel = MessageChannelFactory()
        message_channel_title = "Test Channel"
        message = "Test message"
        action = NotificationChannel.Action.CREATED

        # Call the notify_chat method
        notification = user.notify_chat(
            action=action,
            message=message,
            message_channel_id=message_channel.id,
            message_channel_title=message_channel_title
        )

        # Verify the notification was created
        self.assertIsNotNone(notification)
        self.assertEqual(notification.action, action)
        self.assertEqual(notification.message, message)
        self.assertEqual(notification.channel, user.notification_channel)
        self.assertEqual(notification.tag, "chat")

        # Verify the notification data
        self.assertEqual(notification.data["message_channel_id"], message_channel.id)
        self.assertEqual(notification.data["message_channel_title"], message_channel_title)

        # Verify the notification is in the database
        db_notification = NotificationObject.objects.get(
            channel=user.notification_channel,
            action=action,
            message=message,
            tag="chat"
        )
        self.assertEqual(db_notification.id, notification.id)

    def test_user_notification_subscribe_api(self):
        """Test the UserNotificationSubscribeAPI endpoint"""
        # Create a user
        user = UserFactory()

        # Make a POST request to the UserNotificationSubscribeAPI endpoint
        response = generate_request(
            api=UserNotificationSubscribeAPI,
            data=dict(tags='chat'),
            user=user
        )

        # Verify the response status code
        self.assertEqual(response.status_code, 200)

        # Verify that the user is subscribed to the notification channel
        subscription = NotificationSubscription.objects.get(
            user=user,
            channel=user.notification_channel
        )
        self.assertEqual(set(subscription.tags), {'chat'})

        # Send a notification to the user
        notification = user.notify_chat(
            action=NotificationChannel.Action.CREATED,
            message="Test notification",
            message_channel_id=1,
            message_channel_title="Test Channel"
        )

        # Verify that the user receives the notification
        user_notifications = Notification.objects.filter(
            user=user,
            notification_object__channel=user.notification_channel,
            notification_object__tag="chat"
        )
        self.assertEqual(user_notifications.count(), 1)
        self.assertEqual(user_notifications.first().notification_object, notification)

        # Test unsubscribing (empty tags list)
        response = generate_request(
            api=UserNotificationSubscribeAPI,
            user=user
        )

        # Verify the response status code
        self.assertEqual(response.status_code, 200, response.data)

        # Verify that the user is unsubscribed from the notification channel
        self.assertEqual(
            NotificationSubscription.objects.filter(
                user=user,
                channel=user.notification_channel
            ).count(),
            0
        )
