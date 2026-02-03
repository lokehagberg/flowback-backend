from django.test import TestCase

from flowback.group.notify import (
    notify_group_kanban,
    notify_group_thread,
    notify_group_poll
)
from flowback.group.tests.factories import (
    GroupFactory,
    GroupUserFactory,
    GroupThreadFactory,
    WorkGroupFactory,
    WorkGroupUserFactory
)

from flowback.kanban.tests.factories import KanbanEntryFactory
from flowback.notification.models import NotificationChannel, Notification
from flowback.poll.tests.factories import PollFactory
from flowback.user.tests.factories import UserFactory


class GroupNotificationTest(TestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_user = self.group.group_user_creator
        self.user = self.group_user.user

        # Create a work group
        self.work_group = WorkGroupFactory(group=self.group)
        self.work_group_user = WorkGroupUserFactory(
            group_user=self.group_user,
            work_group=self.work_group
        )

        # Subscribe the user to the notification channel
        self.group.notification_channel.subscribe(user=self.user, tags=['group',
                                                                        'group_user',
                                                                        'kanban',
                                                                        'poll',
                                                                        'thread'])

    def test_notify_group_kanban(self):
        """Test that notify_group_kanban creates a notification in the database"""
        # Create a kanban entry
        kanban_entry = KanbanEntryFactory(
            kanban=self.group.kanban,
            title="Test Kanban Entry",
            work_group=self.work_group
        )

        # Call the function
        message = "Test message"
        action = NotificationChannel.Action.CREATED
        notify_group_kanban(message, action, kanban_entry, self.user)

        # Assert that a notification was created in the database
        self.assertTrue(
            Notification.objects.filter(
                notification_object__channel__object_id=self.group.id,
                notification_object__channel__content_type__model="group",
                notification_object__message=message,
                notification_object__action=action,
                user=self.user
            ).exists()
        )

    def test_notify_group_kanban_with_user_id(self):
        """Test notify_group_kanban with user as an integer ID"""
        # Create a kanban entry
        kanban_entry = KanbanEntryFactory(
            kanban=self.group.kanban,
            title="Test Kanban Entry",
            work_group=self.work_group
        )

        # Create another user to test with
        another_user = UserFactory()

        # Create a group user for the new user
        another_group_user = GroupUserFactory(user=another_user, group=self.group)

        # Add the user to the work group
        WorkGroupUserFactory(group_user=another_group_user, work_group=self.work_group)

        # Subscribe the new user to the notification channel
        subscription = self.group.notification_channel.subscribe(user=another_user, tags=['group', 'kanban'])

        # Call the function with user as an integer ID
        message = "Test message with user ID"
        action = NotificationChannel.Action.CREATED
        notification = notify_group_kanban(message, action, kanban_entry, another_user.id)

        # Assert that a notification was created in the database for the specified user
        self.assertTrue(
            Notification.objects.filter(
                notification_object__channel__object_id=self.group.id,
                notification_object__channel__content_type__model="group",
                notification_object__message=message,
                notification_object__action=action,
                user=another_user
            ).exists()
        )

    def test_notify_group_kanban_without_user(self):
        """Test notify_group_kanban without specifying a user"""
        # Create a kanban entry
        kanban_entry = KanbanEntryFactory(
            kanban=self.group.kanban,
            title="Test Kanban Entry",
            work_group=self.work_group
        )

        # Call the function without specifying a user
        message = "Test message without user"
        action = NotificationChannel.Action.CREATED
        notify_group_kanban(message, action, kanban_entry)

        # Assert that a notification was created in the database for the work group user
        self.assertTrue(
            Notification.objects.filter(
                notification_object__channel__object_id=self.group.id,
                notification_object__channel__content_type__model="group",
                notification_object__message=message,
                notification_object__action=action,
                user=self.user
            ).exists()
        )

    def test_notify_group_kanban_without_work_group(self):
        """Test notify_group_kanban when work_group is None"""
        # Create a kanban entry without a work group
        kanban_entry = KanbanEntryFactory(
            kanban=self.group.kanban,
            title="Test Kanban Entry Without Work Group",
            work_group=None
        )

        # Call the function
        message = "Test message without work group"
        action = NotificationChannel.Action.CREATED
        notify_group_kanban(message, action, kanban_entry, self.user)

        # Assert that a notification was created in the database
        self.assertTrue(
            Notification.objects.filter(
                notification_object__channel__object_id=self.group.id,
                notification_object__channel__content_type__model="group",
                notification_object__message=message,
                notification_object__action=action,
                user=self.user
            ).exists()
        )

    def test_notify_group_thread(self):
        """Test that notify_group_thread creates a notification in the database"""
        # Create a thread with a work group
        thread = GroupThreadFactory(
            created_by=self.group_user,
            title="Test Thread",
            work_group=self.work_group
        )

        # Call the function
        message = "Test thread message"
        action = NotificationChannel.Action.CREATED
        notify_group_thread(message, action, thread)

        # Assert that a notification was created in the database
        self.assertTrue(
            Notification.objects.filter(
                notification_object__channel__object_id=self.group.id,
                notification_object__channel__content_type__model="group",
                notification_object__message=message,
                notification_object__action=action,
                user=self.user
            ).exists()
        )

    def test_notify_group_thread_without_work_group(self):
        """Test notify_group_thread when work_group is None"""
        # Create a thread without a work group
        thread = GroupThreadFactory(
            created_by=self.group_user,
            title="Test Thread Without Work Group",
            work_group=None
        )

        # Call the function
        message = "Test thread message without work group"
        action = NotificationChannel.Action.CREATED
        notify_group_thread(message, action, thread)

        # Assert that a notification was created in the database
        # Since there's no work group, the notification should be sent to all group users
        self.assertTrue(
            Notification.objects.filter(
                notification_object__channel__object_id=self.group.id,
                notification_object__channel__content_type__model="group",
                notification_object__message=message,
                notification_object__action=action
            ).exists()
        )

    def test_notify_group_poll(self):
        """Test that notify_group_poll creates a notification in the database"""
        # Create a poll with a work group
        poll = PollFactory(
            created_by=self.group_user,
            title="Test Poll",
            work_group=self.work_group
        )

        # Call the function
        message = "Test poll message"
        action = NotificationChannel.Action.CREATED
        notify_group_poll(message, action, poll)

        # Assert that a notification was created in the database
        self.assertTrue(
            Notification.objects.filter(
                notification_object__channel__object_id=self.group.id,
                notification_object__channel__content_type__model="group",
                notification_object__message=message,
                notification_object__action=action,
                user=self.user
            ).exists()
        )

    def test_notify_group_poll_without_work_group(self):
        """Test notify_group_poll when work_group is None"""
        # Create a poll without a work group
        poll = PollFactory(
            created_by=self.group_user,
            title="Test Poll Without Work Group",
            work_group=None
        )

        # Call the function
        message = "Test poll message without work group"
        action = NotificationChannel.Action.CREATED
        notify_group_poll(message, action, poll)

        # Assert that a notification was created in the database
        # Since there's no work group, the notification should be sent to all group users
        self.assertTrue(
            Notification.objects.filter(
                notification_object__channel__object_id=self.group.id,
                notification_object__channel__content_type__model="group",
                notification_object__message=message,
                notification_object__action=action
            ).exists()
        )
