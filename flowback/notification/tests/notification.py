import datetime
from rest_framework.test import APITransactionTestCase

from flowback.common.tests import generate_request
from flowback.group.tests.factories import GroupFactory, GroupUserFactory
from flowback.notification.models import NotificationObject, Notification, NotificationSubscription
from flowback.notification.tests.factories import NotificationObjectFactory
from flowback.notification.views import NotificationUpdateAPI, NotificationListAPI
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

    def test_group_notification_subscribe_and_notify(self):
        # Create subscriptions
        group_users = GroupUserFactory.create_batch(size=5, group=self.group)
        [self.group.notification_channel.subscribe(user=u.user,
                                                   tags=['group']) for u in group_users]

        self.assertEqual(
            self.group.notification_channel.notificationsubscription_set.filter(
                channel=self.group.notification_channel).count(), 5)

        # Send notification
        self.group.notify_group(message="Hello everyone!", action=NotificationObject.Action.CREATED)
        self.group.notify_group(message="Hi there!", action=NotificationObject.Action.CREATED)

        self.assertEqual(NotificationObject.objects.count(), 2)
        self.assertEqual(Notification.objects.count(), 10)

        # Check if notifications reached users
        for u in group_users:
            self.assertEqual(Notification.objects.filter(user=u.user,
                                                         notification_object__channel=self.group.notification_channel,
                                                         notification_object__tag="group").count(), 2)

    def test_notification_subscribe_ancestor(self):
        group_users = GroupUserFactory.create_batch(size=5, group=self.group)
        [self.group.notification_channel.subscribe(user=u.user,
                                                   tags=['group']) for u in group_users]

        children = GroupFactory.create_batch(size=5, related_notification_channel=self.group.notification_channel.id)
        GroupFactory.create_batch(size=3, related_notification_channel=children[0].notification_channel)
        nested_children = GroupFactory.create_batch(size=4,
                                                    related_notification_channel=children[1].notification_channel)
        GroupFactory.create_batch(size=4, related_notification_channel=nested_children[1].notification_channel)

        [nested_children[1].notification_channel.subscribe(user=u.user,
                                                           tags=['group']) for u in group_users]

        self.assertEqual(group_users[1].user.notificationsubscription_set.count(), 2)
        self.group.notification_channel.unsubscribe_all(user=group_users[1].user)
        self.assertEqual(group_users[1].user.notificationsubscription_set.count(), 0)

        self.assertEqual(self.group.notification_channel.descendants().count(), 16)

    def test_notification_update(self):
        group_users = GroupUserFactory.create_batch(size=5, group=self.group)
        [self.group.notification_channel.subscribe(user=u.user,
                                                   tags=['group']) for u in group_users]

        notification_one = self.group.notify_group(message="Hello everyone!", action=NotificationObject.Action.CREATED)
        notification_two = self.group.notify_group(message="Hi there!", action=NotificationObject.Action.CREATED)

        # Test updating notification
        response = generate_request(api=NotificationUpdateAPI,
                                    data=dict(notification_object_ids=[notification_two.id], read=True),
                                    user=group_users[1].user)

        self.assertEqual(response.status_code, 200)
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
                                                   tags=['group', 'group_user']) for u in self.group_users]

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
        subscription = self.group.notification_channel.subscribe(user=self.user, tags=['group'])

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
        updated_subscription = self.group.notification_channel.subscribe(user=self.user, tags=['group'])

        # Verify the subscription was updated
        self.assertEqual(updated_subscription.id, subscription.id)  # Same subscription object
        self.assertEqual(set(updated_subscription.tags), {'group'})

        # Test unsubscribing (empty tags list)
        result = self.group.notification_channel.subscribe(user=self.user, tags=[])

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
        group_notification_subscribe(user=self.user, group_id=self.group.id, tags=['group'])

        # Verify the subscription was created
        subscription = NotificationSubscription.objects.get(
            user=self.user,
            channel=self.group.notification_channel
        )
        self.assertEqual(set(subscription.tags), {'group'})

        # Test updating the subscription
        group_notification_subscribe(user=self.user, group_id=self.group.id, tags=[])

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
