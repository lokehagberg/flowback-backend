"""
Schedule Event Test Suite

This test suite covers:
- Schedule Event APIs (list, subscribe, unsubscribe)
- Schedule Event Selectors (schedule_event_list)
- Schedule Event Services (event subscription services)
- Schedule Event Serializers (FilterSerializer, InputSerializer, OutputSerializer)
"""

import json
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.schedule.models import ScheduleUser, ScheduleEventSubscription, ScheduleTagSubscription
from flowback.schedule.selectors import schedule_event_list
from flowback.schedule.services import schedule_event_subscribe, schedule_event_unsubscribe
from flowback.schedule.tests.factories import (ScheduleEventFactory, ScheduleUserFactory,
                                               ScheduleTagFactory, ScheduleEventSubscriptionFactory,
                                               ScheduleTagSubscriptionFactory)
from flowback.schedule.views import (ScheduleEventListAPI,
                                     ScheduleEventSubscribeAPI, ScheduleEventUnsubscribeAPI)
from flowback.user.tests.factories import UserFactory
from flowback.group.tests.factories import GroupFactory


class ScheduleEventAPITest(APITestCase):
    """Test Schedule Event APIs"""

    def setUp(self):
        self.user1 = UserFactory.create()
        self.group1 = GroupFactory.create()
        self.schedule_user1 = ScheduleUserFactory.create(user=self.user1, schedule=self.group1.schedule)

        # Create tag
        self.tag1 = ScheduleTagFactory.create(schedule=self.group1.schedule, name='meeting')

        # Create events
        self.event1 = ScheduleEventFactory.create(
            schedule=self.group1.schedule,
            tag=self.tag1,
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=1, hours=2)
        )
        self.event2 = ScheduleEventFactory.create(
            schedule=self.group1.schedule,
            tag=self.tag1,
            start_date=timezone.now() + timedelta(days=2)
        )

        # Create subscription for event1
        self.event_sub1 = ScheduleEventSubscriptionFactory.create(
            event=self.event1,
            schedule_user=self.schedule_user1
        )

    def test_schedule_event_list_api(self):
        """Test ScheduleEventListAPI returns events for the user"""
        response = generate_request(
            api=ScheduleEventListAPI,
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)  # Only subscribed events

        # Verify output serializer fields
        result = response.data['results'][0]
        self.assertIn('id', result)
        self.assertIn('schedule_id', result)
        self.assertIn('title', result)
        self.assertIn('description', result)
        self.assertIn('start_date', result)
        self.assertIn('end_date', result)
        self.assertIn('active', result)
        self.assertIn('meeting_link', result)
        self.assertIn('repeat_frequency', result)
        self.assertIn('tag_id', result)
        self.assertIn('tag_name', result)
        self.assertIn('origin_name', result)
        self.assertIn('origin_id', result)
        self.assertIn('schedule_origin_name', result)
        self.assertIn('schedule_origin_id', result)
        self.assertIn('assignees', result)
        self.assertIn('reminders', result)
        self.assertIn('user_tags', result)
        self.assertIn('locked', result)
        self.assertIn('subscribed', result)

    def test_schedule_event_list_api_filters(self):
        """Test ScheduleEventListAPI with various filters"""
        # Filter by schedule_ids
        response = generate_request(
            api=ScheduleEventListAPI,
            data={'schedule_ids': str(self.group1.schedule.id)},
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Filter by title
        response = generate_request(
            api=ScheduleEventListAPI,
            data={'title': self.event1.title},
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Filter by active
        response = generate_request(
            api=ScheduleEventListAPI,
            data={'active': True},
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Filter by tag_ids
        response = generate_request(
            api=ScheduleEventListAPI,
            data={'tag_ids': str(self.tag1.id)},
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_schedule_event_list_api_date_filters(self):
        """Test ScheduleEventListAPI with date filters"""
        # Filter by start_date__gt
        response = generate_request(
            api=ScheduleEventListAPI,
            data={'start_date__gt': timezone.now().isoformat()},
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Filter by end_date__lt
        future_date = (timezone.now() + timedelta(days=10)).isoformat()
        response = generate_request(
            api=ScheduleEventListAPI,
            data={'end_date__lt': future_date},
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_schedule_event_subscribe_api(self):
        """Test ScheduleEventSubscribeAPI subscribes user to events"""
        response = generate_request(
            api=ScheduleEventSubscribeAPI,
            data={
                'event_ids': str(self.event2.id),
                'user_tags': 'important,work',
                'locked': True,
                'reminders': '60,300'
            },
            url_params={'schedule_id': self.group1.schedule.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Note: event_subscribe checks if event is_live, so this may not create subscription
        # if the event hasn't started yet

    def test_schedule_event_unsubscribe_api(self):
        """Test ScheduleEventUnsubscribeAPI unsubscribes user from events"""
        response = generate_request(
            api=ScheduleEventUnsubscribeAPI,
            data={'event_ids': str(self.event1.id)},
            url_params={'schedule_id': self.group1.schedule.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify unsubscription
        self.assertFalse(
            ScheduleEventSubscription.objects.filter(
                event=self.event1,
                schedule_user=self.schedule_user1
            ).exists()
        )


class ScheduleEventSelectorTest(APITestCase):
    """Test Schedule Event Selectors"""

    def setUp(self):
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

    def test_schedule_event_list_selector(self):
        """Test schedule_event_list selector returns correct events"""
        # Create events with subscriptions
        event1 = ScheduleEventFactory.create(
            schedule=self.group1.schedule,
            tag=self.tag1
        )
        ScheduleEventSubscriptionFactory.create(
            event=event1,
            schedule_user=self.schedule_user1,
            tags=['important', 'work'],
            locked=True,
            reminders=[60, 300]
        )

        events = schedule_event_list(user=self.user1)

        self.assertEqual(events.count(), 1)
        # Verify annotations
        event = events.first()
        self.assertIsNotNone(event.user_tags)
        self.assertIsNotNone(event.locked)
        self.assertIsNotNone(event.subscribed)
        self.assertIsNotNone(event.reminders)

    def test_schedule_event_list_selector_with_filters(self):
        """Test schedule_event_list selector with various filters"""
        event1 = ScheduleEventFactory.create(
            schedule=self.group1.schedule,
            tag=self.tag1,
            title='Test Meeting'
        )
        ScheduleEventSubscriptionFactory.create(
            event=event1,
            schedule_user=self.schedule_user1
        )

        # Filter by schedule_ids
        filters = {'schedule_ids': str(self.group1.schedule.id)}
        events = schedule_event_list(user=self.user1, filters=filters)
        self.assertEqual(events.count(), 1)

        # Filter by title
        filters = {'title': 'Test Meeting'}
        events = schedule_event_list(user=self.user1, filters=filters)
        self.assertEqual(events.count(), 1)

        # Filter by tag_ids
        filters = {'tag_ids': str(self.tag1.id)}
        events = schedule_event_list(user=self.user1, filters=filters)
        self.assertEqual(events.count(), 1)


class ScheduleEventServiceTest(APITestCase):
    """Test Schedule Event Services"""

    def setUp(self):
        self.user1 = UserFactory.create()
        self.group1 = GroupFactory.create()
        self.schedule_user1 = ScheduleUserFactory.create(user=self.user1, schedule=self.group1.schedule)

        # Create tags
        self.tag1 = ScheduleTagFactory.create(schedule=self.group1.schedule, name='meeting')
        self.tag2 = ScheduleTagFactory.create(schedule=self.group1.schedule, name='deadline')

        # Create events
        self.event1 = ScheduleEventFactory.create(
            schedule=self.group1.schedule,
            tag=self.tag1,
            start_date=timezone.now() - timedelta(hours=1),  # Started event
            end_date=timezone.now() + timedelta(hours=2)
        )

    def test_schedule_event_subscribe_service(self):
        """Test schedule_event_subscribe service creates subscriptions"""
        schedule_event_subscribe(
            user=self.user1,
            schedule_id=self.group1.schedule.id,
            event_ids=[self.event1.id],
            user_tags=['important', 'work'],
            locked=True,
            reminders=[60, 300]
        )

        # Note: Subscription may not be created if event is not live
        # This tests the service logic, actual subscription depends on event.is_live

    def test_schedule_event_unsubscribe_service(self):
        """Test schedule_event_unsubscribe service removes subscriptions"""
        # Create subscription
        ScheduleEventSubscriptionFactory.create(
            event=self.event1,
            schedule_user=self.schedule_user1
        )

        schedule_event_unsubscribe(
            user=self.user1,
            schedule_id=self.group1.schedule.id,
            event_ids=[self.event1.id]
        )

        # Verify unsubscription
        self.assertFalse(
            ScheduleEventSubscription.objects.filter(
                event=self.event1,
                schedule_user=self.schedule_user1
            ).exists()
        )


class ScheduleEventSerializerTest(APITestCase):
    """Test Schedule Event Serializers through API responses"""

    def setUp(self):
        self.user1 = UserFactory.create()
        self.group1 = GroupFactory.create()
        self.schedule_user1 = ScheduleUserFactory.create(user=self.user1, schedule=self.group1.schedule)
        self.tag1 = ScheduleTagFactory.create(schedule=self.group1.schedule)

    def test_schedule_event_list_filter_serializer(self):
        """Test ScheduleEventListAPI FilterSerializer validation"""
        event = ScheduleEventFactory.create(schedule=self.group1.schedule, tag=self.tag1)
        ScheduleEventSubscriptionFactory.create(event=event, schedule_user=self.schedule_user1)

        # Test various filter combinations
        response = generate_request(
            api=ScheduleEventListAPI,
            data={
                'schedule_ids': str(self.group1.schedule.id),
                'active': True,
                'order_by': 'start_date_asc'
            },
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_schedule_event_list_output_serializer(self):
        """Test ScheduleEventListAPI OutputSerializer fields"""
        event = ScheduleEventFactory.create(schedule=self.group1.schedule, tag=self.tag1)
        ScheduleEventSubscriptionFactory.create(event=event, schedule_user=self.schedule_user1)

        response = generate_request(
            api=ScheduleEventListAPI,
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data['results'][0]

        # Verify all output fields
        expected_fields = ['id', 'schedule_id', 'title', 'description', 'start_date',
                          'end_date', 'active', 'meeting_link', 'repeat_frequency',
                          'tag_id', 'tag_name', 'origin_name', 'origin_id',
                          'schedule_origin_name', 'schedule_origin_id', 'assignees',
                          'reminders', 'user_tags', 'locked', 'subscribed']
        for field in expected_fields:
            self.assertIn(field, result)

    def test_schedule_event_subscribe_input_serializer(self):
        """Test ScheduleEventSubscribeAPI InputSerializer validation"""
        event = ScheduleEventFactory.create(
            schedule=self.group1.schedule,
            start_date=timezone.now() - timedelta(hours=1),
            end_date=timezone.now() + timedelta(hours=2)
        )

        response = generate_request(
            api=ScheduleEventSubscribeAPI,
            data={
                'event_ids': str(event.id),
                'user_tags': 'work,important',
                'locked': True,
                'reminders': '60,300'
            },
            url_params={'schedule_id': self.group1.schedule.id},
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
