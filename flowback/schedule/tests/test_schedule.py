from unittest.mock import patch
import datetime

from rest_framework.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from flowback.group.tests.factories import GroupFactory, GroupUserFactory
from flowback.schedule.models import ScheduleEvent, ScheduleSubscription
from flowback.schedule.services import create_event, update_event, delete_event, create_schedule, ScheduleManager, \
    subscribe_schedule, unsubscribe_schedule
from flowback.schedule.selectors import schedule_event_list, ScheduleEventBaseFilter
from flowback.schedule.tasks import event_notify
from flowback.schedule.tests.factories import ScheduleFactory, ScheduleEventFactory


class TestSchedule(TestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_users = GroupUserFactory.create_batch(size=10, group=self.group)

    def test_create_and_update_schedule_event(self):
        event = create_event(
            schedule_id=self.group.schedule.id,
            title="test",
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=1),
            origin_name="test",
            origin_id=1,
            description="test",
            assignee_ids=[x.id for x in self.group_users]
        )
        self.assertEqual(event.assignees.count(), 10)

        update_event(event_id=event.id, data=dict(assignee_ids=[x.id for x in self.group_users[-5:]],
                                                  repeat_frequency=ScheduleEvent.Frequency.DAILY))
        self.assertEqual(event.assignees.count(), 5)

    def test_event_notify(self):
        event = ScheduleEventFactory(
            origin_name="test",
            origin_id=1,
            repeat_frequency=ScheduleEvent.Frequency.DAILY,
            reminders=[0, 120]
        )
        ScheduleEventFactory(
            origin_name="test",
            origin_id=2,
            repeat_frequency=ScheduleEvent.Frequency.DAILY,
            reminders=[0, 120]
        )

        event_notify(event_id=event.id)
        self.assertEqual(len(event.reminders), 2)
        self.assertEqual(PeriodicTask.objects.count(), 2)

        event.delete()
        self.assertEqual(PeriodicTask.objects.count(), 1)


class TestScheduleEventModel(TestCase):
    def setUp(self):
        self.schedule = ScheduleFactory()

    def test_validation_errors(self):
        with self.assertRaises(ValidationError):
            event = ScheduleEventFactory.build(
                schedule=self.schedule,
                start_date=timezone.now() + datetime.timedelta(hours=2),
                end_date=timezone.now() + datetime.timedelta(hours=1)
            )
            event.clean()

        with self.assertRaises(ValidationError):
            event = ScheduleEventFactory.build(
                schedule=self.schedule,
                reminders=[60, 120, 60]
            )
            event.clean()

    def test_valid_configurations(self):
        valid_configs = [
            {'reminders': [60, 120, 300]},
            {'reminders': None},
            {'reminders': []},
            {'start_date': timezone.now(), 'end_date': timezone.now()},
        ]

        for config in valid_configs:
            with self.subTest(config=config):
                event = ScheduleEventFactory.build(schedule=self.schedule, **config)
                event.clean()

    def test_frequency_choices(self):
        self.assertEqual(ScheduleEvent.Frequency.DAILY, 1)
        self.assertEqual(ScheduleEvent.Frequency.WEEKLY, 2)
        self.assertEqual(ScheduleEvent.Frequency.MONTHLY, 3)
        self.assertEqual(ScheduleEvent.Frequency.YEARLY, 4)


class TestScheduleEventSignals(TestCase):
    def setUp(self):
        self.schedule = ScheduleFactory()

    def test_post_save_signal_frequencies(self):
        frequencies = [
            (ScheduleEvent.Frequency.DAILY, {'day_of_week': '*', 'day_of_month': '*', 'month_of_year': '*'}),
            (ScheduleEvent.Frequency.WEEKLY, {'day_of_month': '*', 'month_of_year': '*'}),
            (ScheduleEvent.Frequency.MONTHLY, {'day_of_week': '*', 'month_of_year': '*'}),
            (ScheduleEvent.Frequency.YEARLY, {'day_of_week': '*'}),
        ]

        for frequency, expected_cron_fields in frequencies:
            with self.subTest(frequency=frequency):
                event = ScheduleEventFactory(
                    schedule=self.schedule,
                    reminders=[60],
                    repeat_frequency=frequency
                )
                self.assertEqual(PeriodicTask.objects.count(), 1)
                task = PeriodicTask.objects.get(name=f"schedule_event_{event.id}")

                for field, expected_value in expected_cron_fields.items():
                    self.assertEqual(getattr(task.crontab, field), expected_value)

                PeriodicTask.objects.all().delete()

    def test_post_save_no_reminders(self):
        event = ScheduleEventFactory(
            schedule=self.schedule,
            reminders=None,
            repeat_frequency=ScheduleEvent.Frequency.DAILY
        )
        task = PeriodicTask.objects.get(name=f"schedule_event_{event.id}")
        self.assertTrue(task.one_off)

    def test_post_save_invalid_frequency(self):
        with self.assertRaises(AttributeError):
            ScheduleEventFactory(
                schedule=self.schedule,
                reminders=[60],
                repeat_frequency=99
            )

    def test_pre_delete_signal(self):
        event = ScheduleEventFactory(
            schedule=self.schedule,
            reminders=[60, 120],
            repeat_frequency=ScheduleEvent.Frequency.DAILY
        )
        self.assertEqual(PeriodicTask.objects.count(), 1)
        event.delete()
        self.assertEqual(PeriodicTask.objects.count(), 0)

    def test_post_save_no_repeat_frequency(self):
        ScheduleEventFactory(schedule=self.schedule,
                             reminders=[60, 120],
                             repeat_frequency=None)
        self.assertEqual(PeriodicTask.objects.count(), 0)

    def test_cron_generation(self):
        test_cases = [
            {
                'end_date': timezone.now().replace(hour=14, minute=30, second=0, microsecond=0),
                'frequency': ScheduleEvent.Frequency.DAILY,
                'expected': {'minute': '30', 'hour': '14'}
            },
            {
                'end_date': timezone.now().replace(day=15, hour=9, minute=45, second=0, microsecond=0),
                'frequency': ScheduleEvent.Frequency.MONTHLY,
                'expected': {'minute': '45', 'hour': '9', 'day_of_month': '15'}
            },
        ]

        for case in test_cases:
            with self.subTest(case=case):
                event = ScheduleEventFactory(
                    schedule=self.schedule,
                    end_date=case['end_date'],
                    repeat_frequency=case['frequency']
                )
                task = PeriodicTask.objects.get(name=f"schedule_event_{event.id}")

                for field, expected_value in case['expected'].items():
                    self.assertEqual(getattr(task.crontab, field), expected_value)


class TestScheduleSubscriptionModel(TestCase):
    def test_subscription_validation(self):
        schedule = ScheduleFactory()
        with self.assertRaises(ValidationError):
            subscription = ScheduleSubscription(schedule=schedule, target=schedule)
            subscription.clean()

        schedule2 = ScheduleFactory()
        subscription = ScheduleSubscription(schedule=schedule, target=schedule2)
        subscription.clean()

    def test_unique_together(self):
        schedule1 = ScheduleFactory()
        schedule2 = ScheduleFactory()

        ScheduleSubscription.objects.create(schedule=schedule1, target=schedule2)
        with self.assertRaises(Exception):
            ScheduleSubscription.objects.create(schedule=schedule1, target=schedule2)


class TestScheduleServices(TestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.schedule = self.group.schedule
        self.group_users = GroupUserFactory.create_batch(size=5, group=self.group)

    def test_create_schedule(self):
        schedule = create_schedule(
            name="Test Schedule",
            origin_name="test_origin",
            origin_id=123
        )
        self.assertEqual(schedule.name, "Test Schedule")
        self.assertEqual(schedule.origin_name, "test_origin")
        self.assertEqual(schedule.origin_id, 123)
        self.assertTrue(schedule.active)

    def test_create_event_variations(self):
        base_data = {
            'schedule_id': self.schedule.id,
            'title': "Test Event",
            'start_date': timezone.now(),
            'end_date': timezone.now() + datetime.timedelta(hours=2),
            'origin_name': "test",
            'origin_id': 1
        }

        variations = [
            ({}, {}),
            ({'assignee_ids': [user.id for user in self.group_users[:3]]}, {'assignees__count': 3}),
            ({'reminders': [60, 300], 'repeat_frequency': ScheduleEvent.Frequency.DAILY},
             {'reminders': [60, 300], 'repeat_frequency': ScheduleEvent.Frequency.DAILY}),
        ]

        for extra_data, assertions in variations:
            with self.subTest(extra_data=extra_data):
                event = create_event(**{**base_data, **extra_data})
                for field, expected_value in assertions.items():
                    if '__' in field:
                        self.assertEqual(getattr(event, field.split('__')[0]).count(), expected_value)
                    else:
                        self.assertEqual(getattr(event, field), expected_value)

    def test_update_event(self):
        event = ScheduleEventFactory(schedule=self.schedule)
        original_title = event.title

        updated_event = update_event(event_id=event.id, data={'title': 'Updated Title'})
        self.assertEqual(updated_event.title, 'Updated Title')
        self.assertNotEqual(updated_event.title, original_title)

    def test_delete_event(self):
        event = ScheduleEventFactory(schedule=self.schedule)
        event_id = event.id

        delete_event(event_id=event_id)
        self.assertFalse(ScheduleEvent.objects.filter(id=event_id).exists())

    def test_subscribe_unsubscribe_schedule(self):
        schedule1 = ScheduleFactory()
        schedule2 = ScheduleFactory()

        subscription = subscribe_schedule(schedule_id=schedule1.id, target_id=schedule2.id)
        self.assertEqual(subscription.schedule, schedule1)
        self.assertEqual(subscription.target, schedule2)

        with self.assertRaises(Exception):
            subscribe_schedule(schedule_id=schedule1.id, target_id=schedule2.id)

        unsubscribe_schedule(schedule_id=schedule1.id, target_id=schedule2.id)
        self.assertFalse(ScheduleSubscription.objects.filter(
            schedule=schedule1, target=schedule2
        ).exists())

        with self.assertRaises(Exception):
            unsubscribe_schedule(schedule_id=schedule1.id, target_id=schedule2.id)


class TestScheduleManager(TestCase):
    def setUp(self):
        self.manager = ScheduleManager(schedule_origin_name="test_app")

    def test_manager_initialization(self):
        self.assertEqual(self.manager.origin_name, "test_app")
        self.assertEqual(self.manager.possible_origins, ['test_app'])

        manager = ScheduleManager(
            schedule_origin_name="test_app",
            possible_origins=["app1", "app2"]
        )
        self.assertEqual(manager.possible_origins, ["app1", "app2", 'test_app'])

    def test_schedule_operations(self):
        schedule = self.manager.create_schedule(name="Manager Test Schedule", origin_id=456)
        self.assertEqual(schedule.name, "Manager Test Schedule")
        self.assertEqual(schedule.origin_name, "test_app")
        self.assertEqual(schedule.origin_id, 456)

    def test_event_operations(self):
        schedule = ScheduleFactory(origin_name="test_app", origin_id=123)
        event = ScheduleEventFactory(schedule=schedule)

        retrieved_event = self.manager.get_schedule_event(event.id)
        self.assertEqual(retrieved_event.id, event.id)

        retrieved_event = self.manager.get_schedule_event(event.id, schedule_origin_id=123)
        self.assertEqual(retrieved_event.id, event.id)

        with self.assertRaises(Exception):
            self.manager.get_schedule_event(event.id, schedule_origin_id=999)

        start_date = timezone.now()
        new_event = self.manager.create_event(
            schedule_id=schedule.id,
            title="Manager Created Event",
            start_date=start_date,
            end_date=start_date + datetime.timedelta(hours=2),
            origin_name="test_app",
            origin_id=456
        )
        self.assertEqual(new_event.title, "Manager Created Event")

        updated_event = self.manager.update_event(
            schedule_origin_id=123,
            event_id=new_event.id,
            data={'title': 'Manager Updated Title'}
        )
        self.assertEqual(updated_event.title, 'Manager Updated Title')

        self.manager.delete_event(schedule_origin_id=123, event_id=updated_event.id)
        self.assertFalse(ScheduleEvent.objects.filter(id=updated_event.id).exists())


class TestScheduleSelectors(TestCase):
    def setUp(self):
        self.schedule1 = ScheduleFactory()
        self.schedule2 = ScheduleFactory()

        self.event1 = ScheduleEventFactory(
            schedule=self.schedule1,
            title="Event 1",
            start_date=timezone.now(),
            origin_name="test1"
        )
        self.event2 = ScheduleEventFactory(
            schedule=self.schedule1,
            title="Event 2",
            start_date=timezone.now() + datetime.timedelta(days=1),
            origin_name="test2"
        )
        self.event3 = ScheduleEventFactory(
            schedule=self.schedule2,
            title="Event 3",
            start_date=timezone.now() + datetime.timedelta(days=2),
            origin_name="test3"
        )

    def test_schedule_event_list(self):
        events = schedule_event_list(schedule_id=self.schedule1.id)
        self.assertEqual(events.count(), 2)

        ScheduleSubscription.objects.create(schedule=self.schedule1, target=self.schedule2)
        events = schedule_event_list(schedule_id=self.schedule1.id)
        self.assertEqual(events.count(), 3)

    def test_schedule_event_base_filter(self):
        filter_tests = [
            ({'title': 'Event 1'}, 1),
            ({'origin_name': 'test1'}, 1),
        ]

        for filter_data, expected_count in filter_tests:
            with self.subTest(filter_data=filter_data):
                if 'title' in filter_data:
                    qs = ScheduleEvent.objects.filter(schedule=self.schedule1)
                else:
                    qs = ScheduleEvent.objects.all()

                filtered = ScheduleEventBaseFilter(filter_data, qs)
                self.assertEqual(filtered.qs.count(), expected_count)


class TestScheduleTasks(TestCase):
    def setUp(self):
        self.schedule = ScheduleFactory()

    def test_event_notify_nonexistent(self):
        with self.assertRaises(ScheduleEvent.DoesNotExist):
            event_notify(99999)

    def test_event_notify_frequencies(self):
        frequencies = [
            ScheduleEvent.Frequency.DAILY,
            ScheduleEvent.Frequency.WEEKLY,
            ScheduleEvent.Frequency.MONTHLY,
            ScheduleEvent.Frequency.YEARLY
        ]

        for frequency in frequencies:
            with self.subTest(frequency=frequency):
                event = ScheduleEventFactory(
                    schedule=self.schedule,
                    repeat_frequency=frequency,
                    reminders=[600]
                )
                event_notify(event.id)

    def test_event_notify_with_without_repeat_frequency(self):
        event_with_repeat = ScheduleEventFactory(
            schedule=self.schedule,
            repeat_frequency=ScheduleEvent.Frequency.DAILY,
            reminders=[300, 600]
        )

        with patch("flowback.schedule.tasks.ScheduleEvent.regenerate_notifications") as mock_regen:
            event_notify(event_with_repeat.id)
            mock_regen.assert_called_once()

        event_without_repeat = ScheduleEventFactory(
            schedule=self.schedule,
            repeat_frequency=None,
            reminders=[300]
        )

        call_count = 0

        def mock_regenerate():
            nonlocal call_count
            call_count += 1

        event_without_repeat.regenerate_notifications = mock_regenerate
        event_without_repeat.save()

        event_notify(event_without_repeat.id)
        self.assertEqual(call_count, 0)


class TestScheduleEventProperties(TestCase):
    def setUp(self):
        self.schedule = ScheduleFactory()

    def test_next_dates(self):
        future_start = timezone.now() + datetime.timedelta(hours=2)
        future_end = future_start + datetime.timedelta(hours=1)

        event = ScheduleEventFactory(
            schedule=self.schedule,
            start_date=future_start,
            end_date=future_end,
            repeat_frequency=ScheduleEvent.Frequency.DAILY
        )

        self.assertEqual(event.next_start_date, future_start)
        self.assertEqual(event.next_end_date, future_end)

        past_start = timezone.now() - datetime.timedelta(hours=2)
        past_event = ScheduleEventFactory(
            schedule=self.schedule,
            start_date=past_start,
            repeat_frequency=ScheduleEvent.Frequency.DAILY
        )

        self.assertGreater(past_event.next_start_date, timezone.now())

    def test_regenerate_notifications(self):
        future_start = timezone.now() + datetime.timedelta(hours=2)
        future_end = future_start + datetime.timedelta(hours=1)

        test_cases = [
            {'repeat_frequency': ScheduleEvent.Frequency.DAILY, 'reminders': [300, 600]},
            {'repeat_frequency': ScheduleEvent.Frequency.DAILY, 'reminders': None},
            {'repeat_frequency': None, 'reminders': [300]}
        ]

        for case in test_cases:
            with self.subTest(case=case):
                event = ScheduleEventFactory(
                    schedule=self.schedule,
                    start_date=future_start,
                    end_date=future_end,
                    **case
                )
                event.regenerate_notifications()

    def test_notification_data(self):
        start_date = timezone.now()
        end_date = start_date + datetime.timedelta(hours=2)

        event = ScheduleEventFactory(
            schedule=self.schedule,
            title="Test Event",
            description="Test Description",
            start_date=start_date,
            end_date=end_date,
            origin_name="test_origin",
            origin_id=123
        )

        data = event.notification_data
        expected_fields = ['id', 'title', 'description', 'origin_name', 'origin_id',
                           'schedule_origin_name', 'schedule_origin_id', 'start_date', 'end_date']

        for field in expected_fields:
            self.assertIn(field, data)

        self.assertEqual(data['title'], "Test Event")
        self.assertEqual(data['description'], "Test Description")
        self.assertIsInstance(data['start_date'], str)
        self.assertIsInstance(data['end_date'], str)


class TestScheduleValidation(TestCase):
    def setUp(self):
        self.schedule = ScheduleFactory()

    def test_service_validations(self):
        from flowback.schedule.services import update_schedule
        schedule = ScheduleFactory()

        updated = update_schedule(schedule_id=schedule.id, data={'name': 'Updated Name'})
        self.assertEqual(updated.name, 'Updated Name')

        with self.assertRaises(Exception):
            create_event(
                schedule_id=99999,
                title="Test Event",
                start_date=timezone.now(),
                end_date=timezone.now() + datetime.timedelta(hours=1),
                origin_name="test",
                origin_id=1
            )

    def test_manager_validations(self):
        manager = ScheduleManager("invalid_origin")

        with self.assertRaises(Exception):
            manager.validate_origin_name("wrong_origin")

    def test_event_clean_edge_cases(self):
        event = ScheduleEventFactory.build(schedule=self.schedule, end_date=None)
        event.clean()

        event = ScheduleEventFactory.build(
            schedule=self.schedule,
            reminders=[i for i in range(15)]
        )
        event.clean()
