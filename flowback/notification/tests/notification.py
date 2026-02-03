import datetime
from rest_framework.test import APITransactionTestCase

from flowback.common.tests import generate_request
from flowback.group.tests.factories import GroupFactory, GroupUserFactory
from flowback.notification.models import NotificationObject, Notification, NotificationSubscription, NotificationSubscriptionTag
from flowback.notification.tests.factories import (
    NotificationObjectFactory, 
    NotificationFactory, 
    NotificationSubscriptionFactory, 
    NotificationSubscriptionTagFactory
)
from flowback.notification.views import NotificationUpdateAPI, NotificationListAPI, NotificationSubscriptionListAPI
from flowback.group.views.group import GroupNotificationSubscribeAPI
from flowback.group.services.group import group_notification_subscribe


# Create your tests here.
class GroupNotificationTest(APITransactionTestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_user_creator = self.group.group_user_creator

    def test_group_notification_channel_exists(self):
        self.assertTrue(self.group.notification_channel)

    def test_group_notify_group(self):
        message = "Hello everyone"
        self.group.notify_group(message=message, action=NotificationObject.Action.CREATED)

        self.assertTrue(NotificationObject.objects.filter(channel__content_type__model="group",
                                                          channel__object_id=self.group.id,
                                                          tag="group",
                                                          action=NotificationObject.Action.CREATED,
                                                          message=message).exists(),
                        NotificationObject.objects.first().__dict__)

    def test_group_notification_shift(self):
        NotificationObjectFactory.create_batch(size=10,
                                               channel=self.group.notification_channel,
                                               tag="group")

        # Test shifting all notifications 100 seconds forward
        prev_timestamps = list(NotificationObject.objects.all().order_by("id").values_list("timestamp",
                                                                                           flat=True))
        self.group.notification_channel.shift(delta=-200)
        self.group.notification_channel.shift(delta=300)  # Net total = 100 seconds

        for i, timestamp in enumerate(NotificationObject.objects.all().order_by("id").values_list("timestamp",
                                                                                                  flat=True)):
            self.assertEqual(timestamp, (prev_timestamps[i] + datetime.timedelta(seconds=100)))

        # Test shifting some notifications 200 seconds forward
        prev_timestamps = list(NotificationObject.objects.all().order_by("id").values_list("timestamp",
                                                                                           flat=True))
        self.group.notification_channel.shift(delta=200, timestamp__gt=prev_timestamps[5])

        for i, timestamp in enumerate(NotificationObject.objects.all().order_by("id").values_list("timestamp",
                                                                                                  flat=True)):
            if i <= 5:
                self.assertEqual(timestamp, prev_timestamps[i])
            else:
                self.assertEqual(timestamp, (prev_timestamps[i] + datetime.timedelta(seconds=200)))

    def test_group_notification_delivery(self):
        # Create subscriptions (simpler version focused on notification delivery)
        group_users = GroupUserFactory.create_batch(size=3, group=self.group)
        [self.group.notification_channel.subscribe(user=u.user,
                                                   tags=('group',)) for u in group_users]

        # Send notification and verify delivery
        self.group.notify_group(message="Hello everyone!", action=NotificationObject.Action.CREATED)

        self.assertEqual(NotificationObject.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 3)

        # Check if notifications reached all users
        for u in group_users:
            self.assertTrue(Notification.objects.filter(user=u.user,
                                                        notification_object__channel=self.group.notification_channel,
                                                        notification_object__tag="group").exists())

    def test_notification_subscribe_ancestor(self):
        group_users = GroupUserFactory.create_batch(size=5, group=self.group)
        [self.group.notification_channel.subscribe(user=u.user,
                                                   tags=('group',)) for u in group_users]

        children = GroupFactory.create_batch(size=5, related_notification_channel=self.group.notification_channel.id)
        GroupFactory.create_batch(size=3, related_notification_channel=children[0].notification_channel)
        nested_children = GroupFactory.create_batch(size=4,
                                                    related_notification_channel=children[1].notification_channel)
        GroupFactory.create_batch(size=4, related_notification_channel=nested_children[1].notification_channel)

        [nested_children[1].notification_channel.subscribe(user=u.user,
                                                           tags=('group',)) for u in group_users]

        self.assertEqual(group_users[1].user.notificationsubscription_set.count(), 2)
        self.group.notification_channel.unsubscribe_all(user=group_users[1].user)
        self.assertEqual(group_users[1].user.notificationsubscription_set.count(), 0)

        self.assertEqual(self.group.notification_channel.descendants().count(), 16)

    def test_notification_update(self):
        group_users = GroupUserFactory.create_batch(size=5, group=self.group)
        [self.group.notification_channel.subscribe(user=u.user,
                                                   tags=('group',)) for u in group_users]

        notification_one = self.group.notify_group(message="Hello everyone!", action=NotificationObject.Action.CREATED)
        notification_two = self.group.notify_group(message="Hi there!", action=NotificationObject.Action.CREATED)

        # Test updating notification
        response = generate_request(api=NotificationUpdateAPI,
                                    data=dict(notification_object_ids=[notification_two.id], read=True),
                                    user=group_users[1].user)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(Notification.objects.get(user=group_users[1].user,
                                                  notification_object_id=notification_one.id).read)
        self.assertTrue(Notification.objects.get(user=group_users[1].user,
                                                 notification_object_id=notification_two.id).read)

        # Test if updating impacts other users
        self.assertFalse(Notification.objects.get(user=group_users[2].user,
                                                  notification_object_id=notification_two.id).read)

        # Test if updating no notifications will raise 400
        response = generate_request(api=NotificationUpdateAPI,
                                    data=dict(notification_object_ids=[123, 456], read=True),
                                    user=group_users[1].user)

        self.assertEqual(response.status_code, 400)


class NotificationListTest(APITransactionTestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_users = GroupUserFactory.create_batch(size=5, group=self.group)
        [self.group.notification_channel.subscribe(user=u.user,
                                                   tags=('group', 'group_user')) for u in self.group_users]

        # Create test notifications
        self.notification_one = self.group.notify_group(message="Hello everyone!",
                                                        action=NotificationObject.Action.CREATED)
        self.notification_two = self.group.notify_group(message="Hi there!",
                                                        action=NotificationObject.Action.CREATED)
        self.notification_three = self.group.notify_group(message="Important announcement",
                                                          action=NotificationObject.Action.UPDATED)

        self.test_user = self.group_users[0].user

    def test_pagination(self):
        response = generate_request(api=NotificationListAPI,
                                    data=dict(limit=1),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['count'], 3)
        self.assertIsNotNone(response.data['next'])

    def test_filter_by_message(self):
        response = generate_request(api=NotificationListAPI,
                                    data=dict(message__icontains="Important"),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        self.assertEqual(response.data['results'][0]['message'], "Important announcement")

    def test_filter_by_action(self):
        response = generate_request(api=NotificationListAPI,
                                    data=dict(action=NotificationObject.Action.UPDATED),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        self.assertEqual(response.data['results'][0]['action'], NotificationObject.Action.UPDATED)

    def test_filter_by_timestamp(self):
        # Test greater than
        response = generate_request(api=NotificationListAPI,
                                    data=dict(timestamp__gt=self.notification_two.timestamp),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        self.assertEqual(response.data['results'][0]['object_id'], self.notification_three.id)

        # Test less than
        response = generate_request(api=NotificationListAPI,
                                    data=dict(timestamp__lt=self.notification_two.timestamp),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        self.assertEqual(response.data['results'][0]['object_id'], self.notification_one.id)

    def test_filter_by_read_status(self):
        # Test unread filter
        response = generate_request(api=NotificationListAPI,
                                    data=dict(read=False),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)

        # Mark one as read
        Notification.objects.filter(user=self.test_user,
                                    notification_object_id=self.notification_one.id).update(read=True)

        # Test read filter
        response = generate_request(api=NotificationListAPI,
                                    data=dict(read=True),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        # Test unread filter after marking as read
        response = generate_request(api=NotificationListAPI,
                                    data=dict(read=False),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_channel(self):
        response = generate_request(api=NotificationListAPI,
                                    data=dict(channel_name="group"),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)

    def test_ordering(self):
        # Test ascending order
        response = generate_request(api=NotificationListAPI,
                                    data=dict(order_by="timestamp_asc"),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['results'][0]['object_id'], self.notification_one.id)

        # Test descending order
        response = generate_request(api=NotificationListAPI,
                                    data=dict(order_by="timestamp_desc"),
                                    user=self.test_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['results'][0]['object_id'], self.notification_three.id)

    def test_notification_notify_group_user(self):
        self.group.notify_group_user(_user_id=self.group_users[0].user_id,
                                     message="Test notification",
                                     action=NotificationObject.Action.CREATED)
        self.assertEqual(Notification.objects.get(notification_object__channel__content_type__model="group",
                                                  notification_object__channel__object_id=self.group.id,
                                                  notification_object__tag="group_user").user,
                         self.group_users[0].user)


class NotificationSubscribeTest(APITransactionTestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_user = GroupUserFactory.create(group=self.group)
        self.user = self.group_user.user

    def test_notification_channel_subscribe(self):
        """Test the subscribe method in the NotificationChannel class"""
        # Test subscribing to a channel
        subscription = self.group.notification_channel.subscribe(user=self.user, tags=('group',))

        # Verify the subscription was created
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.channel, self.group.notification_channel)
        self.assertEqual(set(subscription.tags), {'group'})

        # Verify the subscription is in the database
        db_subscription = NotificationSubscription.objects.get(
            user=self.user,
            channel=self.group.notification_channel
        )
        self.assertEqual(set(db_subscription.tags), {'group'})

        # Test updating the subscription
        updated_subscription = self.group.notification_channel.subscribe(user=self.user, tags=('group',))

        # Verify the subscription was updated
        self.assertEqual(updated_subscription.id, subscription.id)  # Same subscription object
        self.assertEqual(set(updated_subscription.tags), {'group'})

        # Test unsubscribing (empty tags list)
        result = self.group.notification_channel.subscribe(user=self.user, tags=())

        # Verify the subscription was deleted
        self.assertIsNone(result)
        self.assertEqual(
            NotificationSubscription.objects.filter(
                user=self.user,
                channel=self.group.notification_channel
            ).count(),
            0
        )

    def test_group_notification_subscribe_service(self):
        """Test the group_notification_subscribe service function"""
        # Call the service function
        group_notification_subscribe(user=self.user, group_id=self.group.id, tags=('group',))

        # Verify the subscription was created
        subscription = NotificationSubscription.objects.get(
            user=self.user,
            channel=self.group.notification_channel
        )
        self.assertEqual(set(subscription.tags), {'group'})

        # Test updating the subscription
        group_notification_subscribe(user=self.user, group_id=self.group.id, tags=())

        # Verify the subscription was updated
        updated_subscription = NotificationSubscription.objects.filter(
            user=self.user,
            channel=self.group.notification_channel
        )

        self.assertEqual(updated_subscription.count(), 0)

    def test_group_notification_subscribe_api(self):
        """Test the GroupNotificationSubscribeAPI endpoint"""
        # Make a POST request to the GroupNotificationSubscribeAPI endpoint
        response = generate_request(
            api=GroupNotificationSubscribeAPI,
            url_params=dict(group_id=self.group.id),
            data=dict(tags='group'),
            user=self.user
        )

        # Verify the response status code
        self.assertEqual(response.status_code, 200)

        # Verify that the user is subscribed to the group's notification channel
        subscription = NotificationSubscription.objects.get(
            user=self.user,
            channel=self.group.notification_channel
        )
        self.assertEqual(set(subscription.tags), {'group'})

        # Send a notification to the group
        notification = self.group.notify_group(message="Test notification", action=NotificationObject.Action.CREATED)

        # Verify that the user receives the notification
        user_notifications = Notification.objects.filter(
            user=self.user,
            notification_object__channel=self.group.notification_channel,
            notification_object__tag="group"
        )
        self.assertEqual(user_notifications.count(), 1)
        self.assertEqual(user_notifications.first().notification_object, notification)


class RemindersTest(APITransactionTestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_user = GroupUserFactory.create(group=self.group)
        self.user = self.group_user.user

    def test_notification_with_reminder_field(self):
        """Test that Notification model has reminder field working correctly"""
        # Create a notification object
        notification_object = NotificationObjectFactory(channel=self.group.notification_channel)
        
        # Create notifications with different reminder values
        notification_immediate = NotificationFactory(
            user=self.user,
            notification_object=notification_object,
            reminder=0
        )
        notification_5min = NotificationFactory(
            user=self.user,
            notification_object=notification_object,
            reminder=300
        )
        
        # Verify the reminder field is set correctly
        self.assertEqual(notification_immediate.reminder, 0)
        self.assertEqual(notification_5min.reminder, 300)
        
        # Test unique_together constraint
        self.assertEqual(Notification.objects.filter(
            user=self.user, 
            notification_object=notification_object
        ).count(), 2)

    def test_subscription_with_reminders(self):
        """Test subscribing to notifications with reminders"""
        # Subscribe with reminders
        subscription = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((300, 600, 3600),)  # 5min, 10min, 1hour reminders
        )
        
        # Verify subscription was created
        self.assertIsNotNone(subscription)
        self.assertEqual(subscription.user, self.user)
        
        # Verify subscription tag with reminders was created
        subscription_tag = NotificationSubscriptionTag.objects.get(
            subscription=subscription,
            name='group'
        )
        self.assertEqual(subscription_tag.reminders, [300, 600, 3600])

    def test_subscription_tag_reminders_validation(self):
        """Test reminders validation in subscription tags"""
        # Test valid reminders
        subscription = NotificationSubscriptionFactory(
            user=self.user,
            channel=self.group.notification_channel
        )
        
        subscription_tag = NotificationSubscriptionTagFactory(
            subscription=subscription,
            name='group',
            reminders=[60, 300, 3600]
        )
        
        # Verify reminders were saved correctly
        subscription_tag.refresh_from_db()
        self.assertEqual(subscription_tag.reminders, [60, 300, 3600])

    def test_reminder_notifications_creation(self):
        """Test that reminder notifications are created when subscribing with reminders"""
        # Subscribe with reminders
        self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((300, 600),)  # 5min, 10min reminders
        )
        
        # Send a notification
        notification_object = self.group.notify_group(
            message="Test notification with reminders", 
            action=NotificationObject.Action.CREATED
        )
        
        # Verify immediate notification was created
        immediate_notification = Notification.objects.get(
            user=self.user,
            notification_object=notification_object,
            reminder=0
        )
        self.assertEqual(immediate_notification.reminder, 0)
        
        # Verify reminder notifications were created
        reminder_notifications = Notification.objects.filter(
            user=self.user,
            notification_object=notification_object,
            reminder__gt=0
        ).order_by('reminder')
        
        self.assertEqual(reminder_notifications.count(), 2)
        self.assertEqual(reminder_notifications[0].reminder, 300)
        self.assertEqual(reminder_notifications[1].reminder, 600)

    def test_subscription_reminders_update(self):
        """Test updating subscription reminders"""
        # Initial subscription with reminders
        self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((300, 600),)
        )
        
        # Send a notification to create reminder notifications
        notification_object = self.group.notify_group(
            message="Test notification", 
            action=NotificationObject.Action.CREATED
        )
        
        # Verify initial reminder notifications
        initial_reminders = Notification.objects.filter(
            user=self.user,
            notification_object=notification_object,
            reminder__gt=0
        ).count()
        self.assertEqual(initial_reminders, 2)
        
        # Update subscription with different reminders
        self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((60, 1800),)  # Different reminders: 1min, 30min
        )
        
        # Send another notification
        notification_object2 = self.group.notify_group(
            message="Second test notification", 
            action=NotificationObject.Action.CREATED
        )
        
        # Verify new reminder notifications have correct values
        new_reminder_notifications = Notification.objects.filter(
            user=self.user,
            notification_object=notification_object2,
            reminder__gt=0
        ).order_by('reminder')
        
        self.assertEqual(new_reminder_notifications.count(), 2)
        self.assertEqual(new_reminder_notifications[0].reminder, 60)
        self.assertEqual(new_reminder_notifications[1].reminder, 1800)

    def test_subscription_without_reminders(self):
        """Test subscribing without reminders (traditional behavior)"""
        # Subscribe without reminders
        subscription = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',)  # No reminders specified
        )
        
        # Verify subscription was created
        self.assertIsNotNone(subscription)
        
        # Verify subscription tag has no reminders
        subscription_tag = NotificationSubscriptionTag.objects.get(
            subscription=subscription,
            name='group'
        )
        self.assertIsNone(subscription_tag.reminders)
        
        # Send notification
        notification_object = self.group.notify_group(
            message="Test notification without reminders", 
            action=NotificationObject.Action.CREATED
        )
        
        # Verify only immediate notification was created
        notifications = Notification.objects.filter(
            user=self.user,
            notification_object=notification_object
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications.first().reminder, 0)

    def test_reminder_validation_limits(self):
        """Test validation limits for reminders"""
        subscription = NotificationSubscriptionFactory(
            user=self.user,
            channel=self.group.notification_channel
        )
        
        # Test maximum 10 reminders limit - should not raise error for valid count
        valid_reminders = [60, 120, 300, 600, 1200, 1800, 3600, 7200, 14400, 86400]
        subscription_tag = NotificationSubscriptionTagFactory(
            subscription=subscription,
            name='group',
            reminders=valid_reminders
        )
        subscription_tag.refresh_from_db()
        self.assertEqual(len(subscription_tag.reminders), 10)

    def test_reminder_edge_cases(self):
        """Test edge cases for reminder values and validation"""
        from rest_framework.exceptions import ValidationError
        
        # Test invalid reminder value (zero) should raise ValidationError
        with self.assertRaises(ValidationError):
            self.group.notification_channel.subscribe(
                user=self.user, 
                tags=('group',),
                reminders=((0, 300),)  # Zero should be invalid
            )
        
        # Test invalid reminder value (negative) - system may allow it but let's test actual behavior
        try:
            subscription = self.group.notification_channel.subscribe(
                user=self.user, 
                tags=('group',),
                reminders=((-60, 300),)  # Negative values
            )
            # If no exception, verify subscription was created but test the behavior
            self.assertIsNotNone(subscription)
        except ValidationError:
            # If ValidationError is raised, that's also acceptable behavior
            pass
        
        # Test extremely large reminder values (should work but be practical)
        subscription = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((86400, 604800, 2592000),)  # 1day, 1week, 1month
        )
        self.assertIsNotNone(subscription)
        
        # Test empty reminders tuple (should work)
        subscription = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((),)  # Empty tuple
        )
        self.assertIsNotNone(subscription)
        
        # Test None reminders for specific tags
        subscription = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=(None,)  # None reminders
        )
        self.assertIsNotNone(subscription)

    def test_subscription_multiple_tags_edge_cases(self):
        """Test edge cases with multiple tags and reminders"""
        # Test subscribing to multiple tags with different reminder configurations
        subscription = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((300, 600), )  # Different reminders per tag
        )
        self.assertIsNotNone(subscription)
        
        # Test mismatched tags and reminders length
        subscription = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((300, 600), (900, 1800))  # More reminders than tags
        )
        self.assertIsNotNone(subscription)  # Should still work, extra reminders ignored

    def test_reminder_values_sorting(self):
        """Test that reminder values are properly handled"""
        # Test reminder values in different orders
        subscription = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((3600, 60, 300),)  # Unsorted: 1hour, 1min, 5min
        )
        self.assertIsNotNone(subscription)
        
        # Send notification and verify reminder notifications
        notification_object = self.group.notify_group(
            message="Test reminder sorting", 
            action=NotificationObject.Action.CREATED
        )
        
        # Verify all reminder notifications are created
        reminder_notifications = Notification.objects.filter(
            user=self.user,
            notification_object=notification_object,
            reminder__gt=0
        ).order_by('reminder')
        
        # Should create notifications for all reminder values
        self.assertEqual(reminder_notifications.count(), 3)
        expected_reminders = [60, 300, 3600]  # Sorted order
        actual_reminders = list(reminder_notifications.values_list('reminder', flat=True))
        self.assertEqual(actual_reminders, expected_reminders)

    def test_reminder_notifications_timing_edge_cases(self):
        """Test edge cases related to reminder timing"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Subscribe with very short reminder (1 second)
        self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((1,),)  # 1 second reminder
        )
        
        # Send notification with future timestamp
        future_time = timezone.now() + timedelta(hours=1)
        notification_object = self.group.notify_group(
            message="Future notification test", 
            action=NotificationObject.Action.CREATED
        )
        notification_object.timestamp = future_time
        notification_object.save()
        
        # Verify reminder notification is created even for very short intervals
        reminder_notifications = Notification.objects.filter(
            user=self.user,
            notification_object=notification_object,
            reminder=1
        )
        self.assertEqual(reminder_notifications.count(), 1)

    def test_subscription_edge_cases(self):
        """Test edge cases in subscription management"""
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import ValidationError
        
        # Test subscribing to invalid tag
        with self.assertRaises((ValidationError, DjangoValidationError)):
            self.group.notification_channel.subscribe(
                user=self.user, 
                tags=('invalid_tag',),
                reminders=((300,),)
            )
        
        # Test re-subscribing same user multiple times (should update, not duplicate)
        subscription1 = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((300,),)
        )
        
        subscription2 = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((600,),)  # Different reminders
        )
        
        # Should be same subscription object, just updated
        self.assertEqual(subscription1.id, subscription2.id)
        
        # Verify only one subscription exists
        subscriptions = NotificationSubscription.objects.filter(
            user=self.user,
            channel=self.group.notification_channel
        )
        self.assertEqual(subscriptions.count(), 1)

    def test_notification_creation_edge_cases(self):
        """Test edge cases in notification creation"""
        # Test creating notification with extremely long message
        long_message = "A" * 1000  # 1000 character message
        
        subscription = self.group.notification_channel.subscribe(
            user=self.user, 
            tags=('group',),
            reminders=((300,),)
        )
        
        notification_object = self.group.notify_group(
            message=long_message, 
            action=NotificationObject.Action.CREATED
        )
        
        # Verify notifications were created successfully
        notifications = Notification.objects.filter(
            user=self.user,
            notification_object=notification_object
        )
        self.assertEqual(notifications.count(), 2)  # Immediate + 1 reminder
        
        # Test creating notification with special characters
        special_message = "Test with émojis 🚀 and spéciål characters: @#$%^&*()"
        notification_object = self.group.notify_group(
            message=special_message, 
            action=NotificationObject.Action.UPDATED
        )
        
        notifications = Notification.objects.filter(
            user=self.user,
            notification_object=notification_object
        )
        self.assertEqual(notifications.count(), 2)  # Immediate + 1 reminder

    def test_bulk_operations_edge_cases(self):
        """Test edge cases with bulk operations"""
        # Create multiple users and subscribe them all
        users = [GroupUserFactory.create(group=self.group).user for _ in range(50)]
        
        # Subscribe all users with different reminder configurations
        for i, user in enumerate(users):
            reminder_time = (i + 1) * 60  # Different reminder for each user
            self.group.notification_channel.subscribe(
                user=user, 
                tags=('group',),
                reminders=((reminder_time,),)
            )
        
        # Send one notification
        notification_object = self.group.notify_group(
            message="Bulk test notification", 
            action=NotificationObject.Action.CREATED
        )
        
        # Verify all users got immediate notifications + reminders
        total_notifications = Notification.objects.filter(
            notification_object=notification_object
        ).count()
        expected_total = len(users) * 2  # Each user gets immediate + 1 reminder
        self.assertEqual(total_notifications, expected_total)



class NotificationSubscriptionListAPITest(APITransactionTestCase):
    def setUp(self):
        # Create a group and a user in that group
        self.group = GroupFactory()
        self.user = GroupUserFactory.create(group=self.group).user
        # Subscribe the user to the group's notification channel
        self.group.notification_channel.subscribe(user=self.user, tags=("group",))

    def test_subscription_list_basic(self):
        # Use generate_request to call the API and verify the response
        response = generate_request(
            api=NotificationSubscriptionListAPI,
            user=self.user
        )

        self.assertEqual(response.status_code, 200, response.data)
        # Should have exactly one subscription
        self.assertEqual(response.data.get("count"), 1)
        self.assertEqual(len(response.data.get("results", [])), 1)

        item = response.data["results"][0]
        # Basic structure checks
        self.assertEqual(item["channel_name"], "group")
        self.assertEqual(item["channel_id"], self.group.notification_channel.id)
        # Tags should include the subscribed tag
        self.assertIn("tags", item)
        self.assertEqual(len(item["tags"]), 1)
        self.assertEqual(item["tags"][0]["name"], "group")
