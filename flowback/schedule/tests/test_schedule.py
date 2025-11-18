"""
Schedule Test Suite

This test suite covers:
- Schedule APIs (list)
- Schedule Selectors (schedule_list)
- Schedule Serializers (FilterSerializer, OutputSerializer)

Note: Schedule Event Create, Update, Delete APIs are not tested as they are not included in the URL patterns.
"""

import json
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.schedule.models import ScheduleUser, ScheduleEventSubscription, ScheduleTagSubscription
from flowback.schedule.selectors import schedule_list
from flowback.schedule.tests.factories import (ScheduleEventFactory, ScheduleUserFactory,
                                               ScheduleTagFactory, ScheduleEventSubscriptionFactory,
                                               ScheduleTagSubscriptionFactory)
from flowback.schedule.views import ScheduleListAPI
from flowback.user.tests.factories import UserFactory
from flowback.group.tests.factories import GroupFactory
class ScheduleAPITest(APITestCase):
    """Test Schedule List APIs"""

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

    def test_schedule_list_api(self):
        """Test ScheduleListAPI returns schedules for the user"""
        response = generate_request(
            api=ScheduleListAPI,
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        # Verify output serializer fields
        result = response.data['results'][0]
        self.assertIn('id', result)
        self.assertIn('origin_name', result)
        self.assertIn('origin_id', result)
        self.assertIn('default_tag', result)
        self.assertIn('available_tags', result)

    def test_schedule_list_api_filters(self):
        """Test ScheduleListAPI with filters"""
        response = generate_request(
            api=ScheduleListAPI,
            data={'id': self.group1.schedule.id},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.group1.schedule.id)

    def test_schedule_list_api_filter_by_origin(self):
        """Test ScheduleListAPI filter by origin_name and origin_id"""
        response = generate_request(
            api=ScheduleListAPI,
            data={'origin_name': 'group', 'origin_ids': str(self.group1.id)},
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['count'], 1)


class ScheduleSelectorTest(APITestCase):
    """Test Schedule Selectors"""

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

    def test_schedule_list_selector(self):
        """Test schedule_list selector returns correct schedules"""
        schedules = schedule_list(user=self.user1)

        self.assertEqual(schedules.count(), 2)
        # Verify annotation
        schedule = schedules.first()
        self.assertIsNotNone(schedule.available_tags)

    def test_schedule_list_selector_with_filters(self):
        """Test schedule_list selector with filters"""
        filters = {'id': self.group1.schedule.id}
        schedules = schedule_list(user=self.user1, filters=filters)

        self.assertEqual(schedules.count(), 1)
        self.assertEqual(schedules.first().id, self.group1.schedule.id)

    def test_schedule_list_selector_filter_by_origin(self):
        """Test schedule_list selector filter by origin_name and origin_id"""
        filters = {
            'origin_name': 'group',
            'origin_ids': str(self.group1.id)
        }
        schedules = schedule_list(user=self.user1, filters=filters)

        self.assertEqual(schedules.count(), 1)


class ScheduleSerializerTest(APITestCase):
    """Test Schedule Serializers through API responses"""

    def setUp(self):
        self.user1 = UserFactory.create()
        self.group1 = GroupFactory.create()
        self.schedule_user1 = ScheduleUserFactory.create(user=self.user1, schedule=self.group1.schedule)
        self.tag1 = ScheduleTagFactory.create(schedule=self.group1.schedule)

    def test_schedule_list_filter_serializer(self):
        """Test ScheduleListAPI FilterSerializer validation"""
        # Test valid filters
        response = generate_request(
            api=ScheduleListAPI,
            data={
                'id': self.group1.schedule.id,
                'origin_name': 'group',
                'origin_id': self.group1.id,
                'order_by': 'created_at_asc'
            },
            user=self.user1
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_schedule_list_output_serializer(self):
        """Test ScheduleListAPI OutputSerializer fields"""
        response = generate_request(
            api=ScheduleListAPI,
            user=self.user1
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data['results'][0]

        # Verify all output fields
        expected_fields = ['id', 'origin_name', 'origin_id', 'default_tag']
        for field in expected_fields:
            self.assertIn(field, result)
