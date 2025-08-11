from pprint import pprint

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.group.tests.factories import GroupFactory, GroupUserFactory
from flowback.group.views.schedule import GroupScheduleEventListAPI, GroupScheduleEventCreateAPI
from flowback.schedule.models import ScheduleEvent
from flowback.schedule.services import create_event
from flowback.schedule.tests.factories import ScheduleFactory, ScheduleEventFactory


class TestSchedule(APITestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_users = GroupUserFactory.create_batch(size=10, group=self.group)

    # Tests if schedule list response correct amount of events, as well as assignees
    def test_group_schedule_list(self):
        create_event(schedule_id=self.group.schedule.id,
                     title="test",
                     start_date=timezone.now(),
                     end_date=timezone.now() + timezone.timedelta(days=1),
                     origin_name="group",
                     origin_id=1,
                     description="test",
                     repeat_frequency=ScheduleEvent.Frequency.DAILY,
                     assignee_ids=[x.id for x in self.group_users])

        # Relevant
        ScheduleEventFactory.create_batch(size=10,
                                          schedule_id=self.group.schedule.id,
                                          origin_id=1,
                                          origin_name="group",
                                          repeat_frequency=ScheduleEvent.Frequency.DAILY)

        # Irrelevant, wrong group
        ScheduleEventFactory.create_batch(size=10,
                                          origin_id=2,
                                          origin_name="group")

        # Irrelevant, wrong origin
        ScheduleEventFactory.create_batch(size=10,
                                          origin_id=1,
                                          origin_name="test")

        response = generate_request(api=GroupScheduleEventListAPI,
                                    user=self.group_users[0].user,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['count'], 11)
        self.assertEqual(len(response.data['results'][0]['assignees']), 10)
        self.assertTrue(all([x.get('repeat_frequency', None) == 'Daily' for x in response.data['results']]),
                        [x.get('repeat_frequency', None) for x in response.data['results']])

    def test_group_schedule_event_create(self):
        # Prepare test data
        start_date = timezone.now()
        end_date = start_date + timezone.timedelta(days=1)
        initial_count = ScheduleEvent.objects.count()
        test_data = {
            'title': 'Test Event',
            'description': 'Test Description',
            'start_date': start_date,
            'end_date': end_date,
            'assignee_ids': [self.group_users[0].id, self.group_users[1].id],
            'reminders': [300, 600],  # 5 and 10 minutes before
            'repeat_frequency': ScheduleEvent.Frequency.WEEKLY
        }

        response = generate_request(
            api=GroupScheduleEventCreateAPI,
            user=self.group_users[0].user,
            data=test_data,
            url_params=dict(group_id=self.group.id)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn('id', response.data)
        self.assertEqual(ScheduleEvent.objects.count(), initial_count + 1)

        # Verify event details
        event = ScheduleEvent.objects.get(id=response.data['id'])
        self.assertEqual(event.title, test_data['title'])
        self.assertEqual(event.description, test_data['description'])
        self.assertEqual(event.repeat_frequency, test_data['repeat_frequency'])
        self.assertEqual(event.reminders, test_data['reminders'])
        self.assertEqual(list(event.assignees.values_list('id', flat=True)), test_data['assignee_ids'])
