from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from rest_framework.test import APITransactionTestCase

from flowback.group.tests.factories import GroupFactory, GroupUserFactory
from flowback.schedule.models import ScheduleEvent
from flowback.schedule.services import create_event, update_event
from flowback.schedule.tasks import event_notify
from flowback.schedule.tests.factories import ScheduleFactory, ScheduleEventFactory


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

    def test_event_notify(self):
        event = ScheduleEventFactory(origin_name="test",
                                     origin_id=1,
                                     repeat_frequency=ScheduleEvent.Frequency.DAILY,
                                     reminders=[0, 120])

        ScheduleEventFactory(origin_name="test",
                             origin_id=2,
                             repeat_frequency=ScheduleEvent.Frequency.DAILY,
                             reminders=[0, 120])

        event_notify(event_id=event.id, seconds_before_event=10)

        self.assertEqual(event.reminder_tasks.count(), 2)
        self.assertEqual(PeriodicTask.objects.count(), 4)

        event.delete()
        self.assertEqual(PeriodicTask.objects.count(), 2)
