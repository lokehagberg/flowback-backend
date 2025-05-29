from pprint import pprint

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.group.tests.factories import GroupFactory, GroupUserFactory
from flowback.group.views.schedule import GroupScheduleEventListAPI
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
