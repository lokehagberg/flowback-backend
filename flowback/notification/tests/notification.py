from rest_framework.test import APITransactionTestCase

from flowback.notification.services import NotificationManager
from flowback.user.tests.factories import UserFactory


class NotificationTest(APITransactionTestCase):
    def setUp(self):
        self.manager = NotificationManager(sender_type="notification", possible_categories=["lorem",
                                                                                            "ipsum",
                                                                                            "dolor"])
        self.user = UserFactory()

    def test_notification_unsubscribe(self):
        channel = self.manager.load_channel(sender_id=1, category='lorem')
        self.manager.channel_subscribe(user_id=self.user.id, sender_id=channel.id, category="lorem")
        self.manager.channel_unsubscribe(user_id=self.user.id, sender_id=channel.id, category="lorem")
