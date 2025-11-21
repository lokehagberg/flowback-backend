"""
User Schedule Test Suite

This test suite covers:
- UserScheduleEventCreateAPI
- UserScheduleEventUpdateAPI
- UserScheduleEventDeleteAPI
"""

from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.schedule.models import ScheduleEvent, ScheduleTag
from flowback.schedule.tests.factories import ScheduleTagFactory
from flowback.user.tests.factories import UserFactory
from flowback.user.views.schedule import (UserScheduleEventCreateAPI,
                                          UserScheduleEventUpdateAPI,
                                          UserScheduleEventDeleteAPI)


class UserScheduleEventCreateAPITest(APITestCase):
    """Test UserScheduleEventCreateAPI"""

    def setUp(self):
        self.user = UserFactory.create()
        self.tag = ScheduleTag.objects.get(schedule=self.user.schedule)

    def test_create_event_success_minimal(self):
        """Test creating a schedule event with minimal required fields"""
        start_date = timezone.now() + timedelta(days=1)
        
        data = {
            'title': 'Team Meeting',
            'start_date': start_date.isoformat(),
        }

        response = generate_request(
            api=UserScheduleEventCreateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        
        # Verify event was created
        event = ScheduleEvent.objects.filter(
            schedule=self.user.schedule,
            title='Team Meeting'
        ).first()
        
        self.assertIsNotNone(event)
        self.assertEqual(event.title, 'Team Meeting')
        self.assertEqual(event.schedule, self.user.schedule)

    def test_create_event_success_full(self):
        """Test creating a schedule event with all fields"""
        start_date = timezone.now() + timedelta(days=1)
        end_date = start_date + timedelta(hours=2)
        
        data = {
            'title': 'Project Review',
            'description': 'Quarterly project review meeting',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'tag': self.tag.name,
            'meeting_link': 'https://meet.example.com/project-review',
            'repeat_frequency': ScheduleEvent.Frequency.WEEKLY,
        }

        response = generate_request(
            api=UserScheduleEventCreateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        
        # Verify event was created with all fields
        event = ScheduleEvent.objects.filter(
            schedule=self.user.schedule,
            title='Project Review'
        ).first()
        
        self.assertIsNotNone(event)
        self.assertEqual(event.title, 'Project Review')
        self.assertEqual(event.description, 'Quarterly project review meeting')
        self.assertEqual(event.schedule, self.user.schedule)
        self.assertEqual(event.meeting_link, 'https://meet.example.com/project-review')
        self.assertEqual(event.repeat_frequency, ScheduleEvent.Frequency.WEEKLY)

    def test_create_event_with_blank_description(self):
        """Test creating an event with blank description"""
        start_date = timezone.now() + timedelta(days=1)
        
        data = {
            'title': 'Quick Sync',
            'description': '',
            'start_date': start_date.isoformat(),
        }

        response = generate_request(
            api=UserScheduleEventCreateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_event_missing_title(self):
        """Test creating an event without required title field"""
        start_date = timezone.now() + timedelta(days=1)
        
        data = {
            'start_date': start_date.isoformat(),
        }

        response = generate_request(
            api=UserScheduleEventCreateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_event_missing_start_date(self):
        """Test creating an event without required start_date field"""
        data = {
            'title': 'Missing Date Event',
        }

        response = generate_request(
            api=UserScheduleEventCreateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_event_unauthenticated(self):
        """Test creating an event without authentication"""
        start_date = timezone.now() + timedelta(days=1)
        
        data = {
            'title': 'Unauthenticated Event',
            'start_date': start_date.isoformat(),
        }

        response = generate_request(
            api=UserScheduleEventCreateAPI,
            data=data,
            user=None
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_event_with_assignees(self):
        """Test creating an event with assignees (should work for user schedule)"""
        start_date = timezone.now() + timedelta(days=1)
        
        data = {
            'title': 'Team Task',
            'start_date': start_date.isoformat(),
            'assignees': '1,2,3',  # Character separated field
        }

        response = generate_request(
            api=UserScheduleEventCreateAPI,
            data=data,
            user=self.user
        )

        # This should succeed at the API level but may fail validation
        # depending on whether user schedules support assignees
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])


class UserScheduleEventUpdateAPITest(APITestCase):
    """Test UserScheduleEventUpdateAPI"""

    def setUp(self):
        self.user = UserFactory.create()
        self.tag = ScheduleTagFactory.create(schedule=self.user.schedule, name='work')
        
        # Create an event to update
        start_date = timezone.now() + timedelta(days=1)
        end_date = start_date + timedelta(hours=1)
        
        self.event = ScheduleEvent.objects.create(
            schedule=self.user.schedule,
            created_by=self.user,
            title='Original Title',
            description='Original description',
            start_date=start_date,
            end_date=end_date,
            tag=self.tag,
            active=True
        )

    def test_update_event_title(self):
        """Test updating event title"""
        data = {
            'event_id': self.event.id,
            'title': 'Updated Title'
        }

        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify event was updated
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, 'Updated Title')
        self.assertEqual(self.event.description, 'Original description')  # Unchanged

    def test_update_event_description(self):
        """Test updating event description"""
        data = {
            'event_id': self.event.id,
            'description': 'Updated description'
        }

        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.event.refresh_from_db()
        self.assertEqual(self.event.description, 'Updated description')

    def test_update_event_dates(self):
        """Test updating event start and end dates"""
        new_start_date = timezone.now() + timedelta(days=2)
        new_end_date = new_start_date + timedelta(hours=3)
        
        data = {
            'event_id': self.event.id,
            'start_date': new_start_date.isoformat(),
            'end_date': new_end_date.isoformat()
        }

        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.event.refresh_from_db()
        # Compare timestamps (strip microseconds for comparison)
        self.assertEqual(
            self.event.start_date.replace(microsecond=0),
            new_start_date.replace(microsecond=0)
        )

    def test_update_event_meeting_link(self):
        """Test updating event meeting link"""
        data = {
            'event_id': self.event.id,
            'meeting_link': 'https://zoom.us/j/12345'
        }

        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.event.refresh_from_db()
        self.assertEqual(self.event.meeting_link, 'https://zoom.us/j/12345')

    def test_update_event_repeat_frequency(self):
        """Test updating event repeat frequency"""
        data = {
            'event_id': self.event.id,
            'repeat_frequency': ScheduleEvent.Frequency.DAILY
        }

        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.event.refresh_from_db()
        self.assertEqual(self.event.repeat_frequency, ScheduleEvent.Frequency.DAILY)

    def test_update_event_multiple_fields(self):
        """Test updating multiple fields at once"""
        new_start_date = timezone.now() + timedelta(days=3)
        new_end_date = timezone.now() + timedelta(days=6)
        
        data = {
            'event_id': self.event.id,
            'title': 'Multi-field Update',
            'description': 'Updated multiple fields',
            'start_date': new_start_date.isoformat(),
            'end_date': new_end_date.isoformat(),
            'meeting_link': 'https://meet.google.com/abc-defg-hij'
        }

        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, 'Multi-field Update')
        self.assertEqual(self.event.description, 'Updated multiple fields')
        self.assertEqual(self.event.meeting_link, 'https://meet.google.com/abc-defg-hij')

    def test_update_event_missing_event_id(self):
        """Test updating without event_id"""
        data = {
            'title': 'No Event ID'
        }

        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_event_nonexistent_event(self):
        """Test updating a non-existent event"""
        data = {
            'event_id': 99999,
            'title': 'Should Fail'
        }

        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_event_unauthenticated(self):
        """Test updating an event without authentication"""
        data = {
            'event_id': self.event.id,
            'title': 'Unauthenticated Update'
        }

        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=data,
            user=None
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_event_clear_optional_fields(self):
        """Test clearing optional fields by setting them to null"""
        data = {
            'event_id': self.event.id,
            'description': None,
            'end_date': None,
            'meeting_link': None
        }

        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        
        self.event.refresh_from_db()
        self.assertIsNone(self.event.description)
        self.assertIsNone(self.event.end_date)
        self.assertIsNone(self.event.meeting_link)


class UserScheduleEventDeleteAPITest(APITestCase):
    """Test UserScheduleEventDeleteAPI"""

    def setUp(self):
        self.user = UserFactory.create()
        self.other_user = UserFactory.create()
        self.tag = ScheduleTagFactory.create(schedule=self.user.schedule, name='task')
        
        # Create an event to delete
        start_date = timezone.now() + timedelta(days=1)
        
        self.event = ScheduleEvent.objects.create(
            created_by=self.user,
            schedule=self.user.schedule,
            title='Event to Delete',
            description='This event will be deleted',
            start_date=start_date,
            tag=self.tag,
            active=True
        )

    def test_delete_event_success(self):
        """Test successfully deleting an event"""
        data = {
            'event_id': self.event.id
        }

        response = generate_request(
            api=UserScheduleEventDeleteAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify event was deleted
        self.assertFalse(
            ScheduleEvent.objects.filter(id=self.event.id).exists()
        )

    def test_delete_event_missing_event_id(self):
        """Test deleting without event_id"""
        data = {}

        response = generate_request(
            api=UserScheduleEventDeleteAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify event still exists
        self.assertTrue(
            ScheduleEvent.objects.filter(id=self.event.id).exists()
        )

    def test_delete_event_nonexistent(self):
        """Test deleting a non-existent event"""
        data = {
            'event_id': 99999
        }

        response = generate_request(
            api=UserScheduleEventDeleteAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_event_unauthenticated(self):
        """Test deleting an event without authentication"""
        data = {
            'event_id': self.event.id
        }

        response = generate_request(
            api=UserScheduleEventDeleteAPI,
            data=data,
            user=None
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Verify event still exists
        self.assertTrue(
            ScheduleEvent.objects.filter(id=self.event.id).exists()
        )

    def test_delete_event_verify_cleanup(self):
        """Test that deleting an event properly removes all related data"""
        event_id = self.event.id
        
        data = {
            'event_id': event_id
        }

        response = generate_request(
            api=UserScheduleEventDeleteAPI,
            data=data,
            user=self.user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify event is completely gone
        self.assertFalse(
            ScheduleEvent.objects.filter(id=event_id).exists()
        )
        
        # Ensure user's schedule still exists
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.schedule)


class UserScheduleEventIntegrationTest(APITestCase):
    """Integration tests for the complete lifecycle of user schedule events"""

    def setUp(self):
        self.user = UserFactory.create()
        self.tag = ScheduleTagFactory.create(schedule=self.user.schedule, name='personal')

    def test_create_update_delete_lifecycle(self):
        """Test creating, updating, and deleting an event in sequence"""
        start_date = timezone.now() + timedelta(days=1)
        
        # Create event
        create_data = {
            'title': 'Lifecycle Event',
            'description': 'Testing full lifecycle',
            'start_date': start_date.isoformat(),
        }

        create_response = generate_request(
            api=UserScheduleEventCreateAPI,
            data=create_data,
            user=self.user
        )

        self.assertEqual(create_response.status_code, status.HTTP_200_OK)
        
        # Find the created event
        event = ScheduleEvent.objects.filter(
            schedule=self.user.schedule,
            title='Lifecycle Event'
        ).first()
        
        self.assertIsNotNone(event)
        event_id = event.id
        
        # Update event
        update_data = {
            'event_id': event_id,
            'title': 'Updated Lifecycle Event',
            'description': 'Updated description'
        }

        update_response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=update_data,
            user=self.user
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        event.refresh_from_db()
        self.assertEqual(event.title, 'Updated Lifecycle Event')
        self.assertEqual(event.description, 'Updated description')
        
        # Delete event
        delete_data = {
            'event_id': event_id
        }

        delete_response = generate_request(
            api=UserScheduleEventDeleteAPI,
            data=delete_data,
            user=self.user
        )

        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        
        # Verify event is gone
        self.assertFalse(
            ScheduleEvent.objects.filter(id=event_id).exists()
        )

    def test_multiple_events_same_user(self):
        """Test creating and managing multiple events for the same user"""
        start_date = timezone.now() + timedelta(days=1)
        
        # Create first event
        event1_data = {
            'title': 'Event 1',
            'start_date': start_date.isoformat(),
        }
        
        response1 = generate_request(
            api=UserScheduleEventCreateAPI,
            data=event1_data,
            user=self.user
        )
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Create second event
        event2_data = {
            'title': 'Event 2',
            'start_date': (start_date + timedelta(hours=2)).isoformat(),
        }
        
        response2 = generate_request(
            api=UserScheduleEventCreateAPI,
            data=event2_data,
            user=self.user
        )
        
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Verify both events exist
        events = ScheduleEvent.objects.filter(schedule=self.user.schedule)
        self.assertEqual(events.count(), 2)
        
        event_titles = [e.title for e in events]
        self.assertIn('Event 1', event_titles)
        self.assertIn('Event 2', event_titles)

    def test_user_schedule_isolation(self):
        """Test that users can only access their own schedule events"""
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        
        tag1 = ScheduleTagFactory.create(schedule=user1.schedule, name='user1_tag')
        
        start_date = timezone.now() + timedelta(days=1)
        
        # Create event for user1
        event1 = ScheduleEvent.objects.create(
            created_by=user1,
            schedule=user1.schedule,
            title='User 1 Event',
            start_date=start_date,
            tag=tag1,
            active=True
        )
        
        # Verify schedules are different
        self.assertNotEqual(user1.schedule.id, user2.schedule.id)
        
        # User2 should not be able to update user1's event
        update_data = {
            'event_id': event1.id,
            'title': 'Hacked by User 2'
        }
        
        response = generate_request(
            api=UserScheduleEventUpdateAPI,
            data=update_data,
            user=user2
        )
        
        # Should fail because the event belongs to a different schedule
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify event was not modified
        event1.refresh_from_db()
        self.assertEqual(event1.title, 'User 1 Event')
