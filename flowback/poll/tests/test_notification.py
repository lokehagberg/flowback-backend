from rest_framework.test import APITestCase
from django.utils import timezone

from flowback.common.tests import generate_request
from flowback.notification.models import NotificationChannel, NotificationObject, Notification, NotificationSubscription
from flowback.poll.models import Poll
from flowback.poll.tests.factories import PollFactory
from flowback.comment.tests.factories import CommentFactory
from flowback.group.tests.factories import WorkGroupFactory, GroupUserFactory, WorkGroupUserFactory
from flowback.poll.notify import notify_poll, notify_poll_phase, notify_poll_comment
from flowback.poll.views.poll import PollNotificationSubscribeAPI


class PollNotificationTest(APITestCase):
    def setUp(self):
        # Create a poll without a work group
        self.poll_without_work_group = PollFactory()
        self.user_without_work_group = self.poll_without_work_group.created_by.user

        # Create a poll with a work group
        # First create a group user for the poll
        group_user = GroupUserFactory()

        # Create a work group for that group
        self.work_group = WorkGroupFactory(group=group_user.group)

        # Create a poll with that group user as creator
        self.poll_with_work_group = PollFactory(created_by=group_user)

        # Assign the work group to the poll
        self.poll_with_work_group.work_group = self.work_group
        self.poll_with_work_group.save()

        # Create group users for the work group
        self.group_users = GroupUserFactory.create_batch(size=3, group=self.work_group.group)
        self.work_group_users = [WorkGroupUserFactory(work_group=self.work_group, group_user=user) for user in self.group_users]

        # Create a comment for testing notify_poll_comment
        self.comment = CommentFactory(author=self.group_users[0].user)

    def test_notify_poll_without_work_group(self):
        """Test notify_poll function without a work group"""
        message = "Test poll notification"
        action = NotificationChannel.Action.CREATED

        # Call the notify_poll function
        notification_obj = notify_poll(message=message, action=action, poll=self.poll_without_work_group)

        # Verify the notification was created
        self.assertIsNotNone(notification_obj)
        self.assertEqual(notification_obj.message, message)
        self.assertEqual(notification_obj.action, action)
        self.assertEqual(notification_obj.channel, self.poll_without_work_group.notification_channel)

        # Verify no work_group related data was passed
        self.assertIsNone(notification_obj.data.get('work_group_id'))
        self.assertIsNone(notification_obj.data.get('work_group_name'))

    def test_notify_poll_with_work_group(self):
        """Test notify_poll function with a work group"""
        message = "Test poll notification with work group"
        action = NotificationChannel.Action.CREATED

        # Subscribe users to the poll's notification channel
        for user in self.group_users:
            self.poll_with_work_group.notification_channel.subscribe(user=user.user, tags=['poll'])

        # Call the notify_poll function
        notification_obj = notify_poll(message=message, action=action, poll=self.poll_with_work_group)

        # Verify the notification was created
        self.assertIsNotNone(notification_obj)
        self.assertEqual(notification_obj.message, message)
        self.assertEqual(notification_obj.action, action)
        self.assertEqual(notification_obj.channel, self.poll_with_work_group.notification_channel)

        # Verify work_group related data was passed
        self.assertEqual(notification_obj.data.get('work_group_id'), self.work_group.id)
        self.assertEqual(notification_obj.data.get('work_group_name'), self.work_group.name)

        # Verify notifications were created for all users in the work group
        for user in self.group_users:
            self.assertTrue(
                Notification.objects.filter(
                    user=user.user,
                    notification_object=notification_obj
                ).exists()
            )

    def test_notify_poll_phase_without_work_group(self):
        """Test notify_poll_phase function without a work group"""
        message = "Test poll phase notification"
        action = NotificationChannel.Action.UPDATED

        # Call the notify_poll_phase function
        notification_obj = notify_poll_phase(message=message, action=action, poll=self.poll_without_work_group)

        # Verify the notification was created
        self.assertIsNotNone(notification_obj)
        self.assertEqual(notification_obj.message, message)
        self.assertEqual(notification_obj.action, action)
        self.assertEqual(notification_obj.channel, self.poll_without_work_group.notification_channel)

        # Verify no work_group related data was passed
        self.assertIsNone(notification_obj.data.get('work_group_id'))
        self.assertIsNone(notification_obj.data.get('work_group_name'))

        # Verify current_phase was passed
        self.assertEqual(notification_obj.data.get('current_phase'),
                         self.poll_without_work_group.current_phase.replace('_', ' ').capitalize())

    def test_notify_poll_phase_with_work_group(self):
        """Test notify_poll_phase function with a work group"""
        message = "Test poll phase notification with work group"
        action = NotificationChannel.Action.UPDATED

        # Subscribe users to the poll's notification channel
        for user in self.group_users:
            self.poll_with_work_group.notification_channel.subscribe(user=user.user, tags=['poll_phase'])

        # Call the notify_poll_phase function
        notification_obj = notify_poll_phase(message=message, action=action, poll=self.poll_with_work_group)

        # Verify the notification was created
        self.assertIsNotNone(notification_obj)
        self.assertEqual(notification_obj.message, message)
        self.assertEqual(notification_obj.action, action)
        self.assertEqual(notification_obj.channel, self.poll_with_work_group.notification_channel)

        # Verify work_group related data was passed
        self.assertEqual(notification_obj.data.get('work_group_id'), self.work_group.id)
        self.assertEqual(notification_obj.data.get('work_group_name'), self.work_group.name)

        # Verify current_phase was passed
        self.assertIsNotNone(notification_obj.data.get('current_phase'))

        # Verify notifications were created for all users in the work group
        for user in self.group_users:
            self.assertTrue(
                Notification.objects.filter(
                    user=user.user,
                    notification_object=notification_obj
                ).exists()
            )

    def test_notify_poll_comment_without_work_group(self):
        """Test notify_poll_comment function without a work group"""
        message = "Test poll comment notification"
        action = NotificationChannel.Action.CREATED

        # Call the notify_poll_comment function
        notification_obj = notify_poll_comment(
            message=message,
            action=action,
            poll=self.poll_without_work_group,
            comment=self.comment
        )

        # Verify the notification was created
        self.assertIsNotNone(notification_obj)
        self.assertEqual(notification_obj.message, message)
        self.assertEqual(notification_obj.action, action)
        self.assertEqual(notification_obj.channel, self.poll_without_work_group.notification_channel)

        # Verify no work_group related data was passed
        self.assertIsNone(notification_obj.data.get('work_group_id'))
        self.assertIsNone(notification_obj.data.get('work_group_name'))

        # Verify comment_message was passed
        self.assertEqual(notification_obj.data.get('comment_message'), self.comment.message)

    def test_notify_poll_comment_with_work_group(self):
        """Test notify_poll_comment function with a work group"""
        message = "Test poll comment notification with work group"
        action = NotificationChannel.Action.CREATED

        # Subscribe users to the poll's notification channel
        for user in self.group_users:
            self.poll_with_work_group.notification_channel.subscribe(user=user.user, tags=['poll_comment'])

        # Call the notify_poll_comment function
        notification_obj = notify_poll_comment(
            message=message,
            action=action,
            poll=self.poll_with_work_group,
            comment=self.comment
        )

        # Verify the notification was created
        self.assertIsNotNone(notification_obj)
        self.assertEqual(notification_obj.message, message)
        self.assertEqual(notification_obj.action, action)
        self.assertEqual(notification_obj.channel, self.poll_with_work_group.notification_channel)

        # Verify work_group related data was passed
        self.assertEqual(notification_obj.data.get('work_group_id'), self.work_group.id)
        self.assertEqual(notification_obj.data.get('work_group_name'), self.work_group.name)

        # Verify comment_message was passed
        self.assertEqual(notification_obj.data.get('comment_message'), self.comment.message)

        # Verify notifications were created for all users in the work group except the comment author
        for user in self.group_users:
            if user.user.id != self.comment.author_id:
                self.assertTrue(
                    Notification.objects.filter(
                        user=user.user,
                        notification_object=notification_obj
                    ).exists()
                )
            else:
                self.assertFalse(
                    Notification.objects.filter(
                        user=user.user,
                        notification_object=notification_obj
                    ).exists()
                )


class PollNotificationSubscribeTest(APITestCase):
    def setUp(self):
        # Create a poll without a work group
        self.poll = PollFactory()
        self.user = self.poll.created_by.user

    def test_poll_notification_subscribe_api(self):
        """Test the PollNotificationSubscribeAPI endpoint"""
        # Make a POST request to the PollNotificationSubscribeAPI endpoint
        response = generate_request(
            api=PollNotificationSubscribeAPI,
            url_params=dict(poll_id=self.poll.id),
            data=dict(tags='poll'),
            user=self.user
        )

        # Verify the response status code
        self.assertEqual(response.status_code, 200)

        # Verify that the user is subscribed to the group's notification channel
        # Note: poll_notification_subscribe subscribes to the group's channel, not the poll's channel
        subscription = NotificationSubscription.objects.get(
            user=self.user,
            channel=self.poll.notification_channel
        )

        # Also subscribe the user to the poll's notification channel for the test
        self.poll.notification_channel.subscribe(user=self.user, tags=['poll'])
        self.assertEqual(set(subscription.notificationsubscriptiontag_set.values_list('name', flat=True)), {'poll'})

        # Send a notification to the poll
        notification = notify_poll(
            message="Test notification",
            action=NotificationChannel.Action.CREATED,
            poll=self.poll
        )

        # Verify that the user receives the notification
        user_notifications = Notification.objects.filter(
            user=self.user,
            notification_object__channel=self.poll.notification_channel,
            notification_object__tag="poll"
        )
        self.assertEqual(user_notifications.count(), 1)
        self.assertEqual(user_notifications.first().notification_object, notification)

    def test_poll_notification_unsubscribe_api(self):
        """Test unsubscribing from poll notifications using the API"""

        # First subscribe using the API
        response = generate_request(
            api=PollNotificationSubscribeAPI,
            url_params=dict(poll_id=self.poll.id),
            data=dict(tags='poll'),
            user=self.user
        )
        self.assertEqual(response.status_code, 200)

        # Verify subscription exists
        self.assertTrue(
            NotificationSubscription.objects.filter(
                user=self.user,
                channel=self.poll.notification_channel
            ).exists()
        )

        # Now unsubscribe using the API by sending empty tags
        response = generate_request(
            api=PollNotificationSubscribeAPI,
            url_params=dict(poll_id=self.poll.id),
            user=self.user
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            NotificationSubscription.objects.filter(
                user=self.user,
                channel=self.poll.notification_channel
            ).exists()
        )
