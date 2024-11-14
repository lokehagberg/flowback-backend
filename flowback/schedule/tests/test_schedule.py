from django.utils import timezone
from rest_framework.test import APITransactionTestCase

from flowback.group.tests.factories import GroupFactory, GroupUserFactory
from flowback.schedule.services import create_event, update_event
from flowback.schedule.tests.factories import ScheduleFactory


class TestSchedule(APITransactionTestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_users = GroupUserFactory.create_batch(size=10, group=self.group)

    def test_create_schedule_event(self):
        event = create_event(schedule_id=self.group.schedule.id,
                             title="test",
                             start_date=timezone.now(),
                             end_date=timezone.now() + timezone.timedelta(days=1),
                             origin_name="test",
                             origin_id=1,
                             description="test",
                             assignee_ids=[x.id for x in self.group_users])

        self.assertEqual(event.assignees.count(), 10)
        return event

    def test_update_schedule_event(self):
        event = self.test_create_schedule_event()
        update_event(event_id=event.id, data=dict(assignee_ids=[x.id for x in self.group_users[-5:]]))

        self.assertEqual(event.assignees.count(), 5)
