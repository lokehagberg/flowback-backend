"""
Schedule Subscription Test Suite

This test suite covers:
- Schedule Subscription APIs (subscribe to new tags, unsubscribe from new tags)
- Schedule Tag APIs (subscribe, unsubscribe)
- Schedule Services (all subscription services)
- Schedule Subscription Serializers (FilterSerializer, InputSerializer)
"""

import json
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.schedule.models import ScheduleUser, ScheduleEventSubscription, ScheduleTagSubscription
from flowback.schedule.services import (schedule_tag_subscribe, schedule_tag_unsubscribe,
                                        schedule_subscribe_to_new_tags, schedule_unsubscribe_to_new_tags)
from flowback.schedule.tests.factories import (ScheduleEventFactory, ScheduleUserFactory,
                                               ScheduleTagFactory, ScheduleEventSubscriptionFactory,
                                               ScheduleTagSubscriptionFactory)
from flowback.schedule.views import (ScheduleSubscribeAPI, ScheduleUnsubscribeAPI,
                                     ScheduleTagSubscribeAPI, ScheduleTagUnsubscribeAPI)
from flowback.user.tests.factories import UserFactory
from flowback.group.tests.factories import GroupFactory


class ScheduleSubscriptionAPITest(APITestCase):
    """Test Schedule Subscription APIs"""

    def setUp(self):
        # Create users
        self.user1 = UserFactory.create()
        self.user2 = UserFactory.create()

        # Create groups with schedules
        self.group1 = GroupFactory.create()
        self.group2 = GroupFactory.create()

        # Create schedule users
        self.schedule_user1 = ScheduleUserFactory.create(user=self.user1, schedule=self.group1.schedule)
        self.schedule_user2 = ScheduleUserFactory.create(user=self.user1, schedule=self.group2.schedule)

        # Create tags
        self.tag1 = ScheduleTagFactory.create(schedule=self.group1.schedule, name='meeting')
        self.tag2 = ScheduleTagFactory.create(schedule=self.group1.schedule, name='deadline')

    def test_schedule_subscribe_api(self):
        """Test ScheduleSubscribeAPI subscribes user to new tags"""
        response = generate_request(
            api=ScheduleSubscribeAPI,
            data={'reminders': '60,300'},
            url_params={'schedule_id': self.group1.schedule.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify subscription
        schedule_user = ScheduleUser.objects.get(user=self.user1, schedule=self.group1.schedule)
        self.assertTrue(schedule_user.subscribe_to_new_notification_tags)
        self.assertEqual(schedule_user.reminders, [60, 300])

    def test_schedule_unsubscribe_api(self):
        """Test ScheduleUnsubscribeAPI unsubscribes user from new tags"""
        # First subscribe
        self.schedule_user1.subscribe_to_new_notification_tags = True
        self.schedule_user1.reminders = [60, 300]
        self.schedule_user1.save()

        response = generate_request(
            api=ScheduleUnsubscribeAPI,
            url_params={'schedule_id': self.group1.schedule.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify unsubscription
        schedule_user = ScheduleUser.objects.get(user=self.user1, schedule=self.group1.schedule)
        self.assertFalse(schedule_user.subscribe_to_new_notification_tags)
        self.assertIsNone(schedule_user.reminders)


class ScheduleTagAPITest(APITestCase):
    """Test Schedule Tag APIs"""

    def setUp(self):
        self.user1 = UserFactory.create()
        self.group1 = GroupFactory.create()
        self.schedule_user1 = ScheduleUserFactory.create(user=self.user1, schedule=self.group1.schedule)

        # Create tags
        self.tag1 = ScheduleTagFactory.create(schedule=self.group1.schedule, name='meeting')
        self.tag2 = ScheduleTagFactory.create(schedule=self.group1.schedule, name='deadline')

    def test_schedule_tag_subscribe_api(self):
        """Test ScheduleTagSubscribeAPI subscribes user to tags"""
        response = generate_request(
            api=ScheduleTagSubscribeAPI,
            data={
                'tag_ids': f'{self.tag1.id},{self.tag2.id}',
                'reminders': '60,300'
            },
            url_params={'schedule_id': self.group1.schedule.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify subscriptions
        self.assertTrue(
            ScheduleTagSubscription.objects.filter(
                schedule_user=self.schedule_user1,
                schedule_tag=self.tag1
            ).exists()
        )
        self.assertTrue(
            ScheduleTagSubscription.objects.filter(
                schedule_user=self.schedule_user1,
                schedule_tag=self.tag2
            ).exists()
        )

    def test_schedule_tag_unsubscribe_api(self):
        """Test ScheduleTagUnsubscribeAPI unsubscribes user from tags"""
        # First subscribe
        ScheduleTagSubscriptionFactory.create(
            schedule_user=self.schedule_user1,
            schedule_tag=self.tag1
        )

        response = generate_request(
            api=ScheduleTagUnsubscribeAPI,
            data={'tag_ids': str(self.tag1.id)},
            url_params={'schedule_id': self.group1.schedule.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify unsubscription
        self.assertFalse(
            ScheduleTagSubscription.objects.filter(
                schedule_user=self.schedule_user1,
                schedule_tag=self.tag1
            ).exists()
        )


class ScheduleSubscriptionServiceTest(APITestCase):
    """Test Schedule Subscription Services"""

    def setUp(self):
        self.user1 = UserFactory.create()
        self.group1 = GroupFactory.create()
        self.schedule_user1 = ScheduleUserFactory.create(user=self.user1, schedule=self.group1.schedule)

        # Create tags
        self.tag1 = ScheduleTagFactory.create(schedule=self.group1.schedule, name='meeting')
        self.tag2 = ScheduleTagFactory.create(schedule=self.group1.schedule, name='deadline')

    def test_schedule_tag_subscribe_service(self):
        """Test schedule_tag_subscribe service creates tag subscriptions"""
        schedule_tag_subscribe(
            user=self.user1,
            schedule_id=self.group1.schedule.id,
            tag_ids=[self.tag1.id, self.tag2.id],
            reminders=[60, 300]
        )

        # Verify subscriptions
        self.assertTrue(
            ScheduleTagSubscription.objects.filter(
                schedule_user=self.schedule_user1,
                schedule_tag=self.tag1
            ).exists()
        )
        self.assertTrue(
            ScheduleTagSubscription.objects.filter(
                schedule_user=self.schedule_user1,
                schedule_tag=self.tag2
            ).exists()
        )

    def test_schedule_tag_unsubscribe_service(self):
        """Test schedule_tag_unsubscribe service removes tag subscriptions"""
        # Create subscription
        ScheduleTagSubscriptionFactory.create(
            schedule_user=self.schedule_user1,
            schedule_tag=self.tag1
        )

        schedule_tag_unsubscribe(
            user=self.user1,
            schedule_id=self.group1.schedule.id,
            tag_ids=[self.tag1.id]
        )

        # Verify unsubscription
        self.assertFalse(
            ScheduleTagSubscription.objects.filter(
                schedule_user=self.schedule_user1,
                schedule_tag=self.tag1
            ).exists()
        )

    def test_schedule_subscribe_to_new_tags_service(self):
        """Test schedule_subscribe_to_new_tags service enables new tag subscription"""
        schedule_subscribe_to_new_tags(
            user=self.user1,
            schedule_id=self.group1.schedule.id,
            reminders=[60, 300]
        )

        # Verify subscription
        schedule_user = ScheduleUser.objects.get(user=self.user1, schedule=self.group1.schedule)
        self.assertTrue(schedule_user.subscribe_to_new_notification_tags)
        self.assertEqual(schedule_user.reminders, [60, 300])

    def test_schedule_unsubscribe_to_new_tags_service(self):
        """Test schedule_unsubscribe_to_new_tags service disables new tag subscription"""
        # First enable
        self.schedule_user1.subscribe_to_new_notification_tags = True
        self.schedule_user1.reminders = [60, 300]
        self.schedule_user1.save()

        schedule_unsubscribe_to_new_tags(
            user=self.user1,
            schedule_id=self.group1.schedule.id
        )

        # Verify unsubscription
        schedule_user = ScheduleUser.objects.get(user=self.user1, schedule=self.group1.schedule)
        self.assertFalse(schedule_user.subscribe_to_new_notification_tags)
        self.assertIsNone(schedule_user.reminders)


class ScheduleSubscriptionSerializerTest(APITestCase):
    """Test Schedule Subscription Serializers through API responses"""

    def setUp(self):
        self.user1 = UserFactory.create()
        self.group1 = GroupFactory.create()
        self.schedule_user1 = ScheduleUserFactory.create(user=self.user1, schedule=self.group1.schedule)
        self.tag1 = ScheduleTagFactory.create(schedule=self.group1.schedule)

    def test_schedule_subscribe_input_serializer(self):
        """Test ScheduleSubscribeAPI InputSerializer validation"""
        # Test valid data
        response = generate_request(
            api=ScheduleSubscribeAPI,
            data={'reminders': '60,300,600'},
            url_params={'schedule_id': self.group1.schedule.id},
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_schedule_tag_subscribe_input_serializer(self):
        """Test ScheduleTagSubscribeAPI InputSerializer validation"""
        response = generate_request(
            api=ScheduleTagSubscribeAPI,
            data={
                'tag_ids': str(self.tag1.id),
                'reminders': '60,300'
            },
            url_params={'schedule_id': self.group1.schedule.id},
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
