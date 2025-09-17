import datetime
import json

from celery.schedules import crontab
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models.signals import post_save, post_delete, pre_delete
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from rest_framework.exceptions import ValidationError

from flowback.common.models import BaseModel
from django.utils.translation import gettext_lazy as _

from flowback.notification.models import NotifiableModel, NotificationObject


# Create your models here.
class Schedule(BaseModel):
    name = models.TextField()
    origin_name = models.CharField(max_length=255)
    origin_id = models.IntegerField()

    active = models.BooleanField(default=True)


class ScheduleEvent(BaseModel, NotifiableModel):
    class Frequency(models.IntegerChoices):
        DAILY = 1, _("Daily")
        WEEKLY = 2, _("Weekly")
        MONTHLY = 3, _("Monthly")  # If event start_date day is 29 or higher, skip months that has these dates
        YEARLY = 4, _("Yearly")

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    title = models.TextField()
    description = models.TextField(null=True, blank=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    work_group = models.ForeignKey('group.WorkGroup', on_delete=models.CASCADE, null=True, blank=True)
    assignees = models.ManyToManyField('group.GroupUser')
    meeting_link = models.URLField(null=True, blank=True)

    origin_name = models.CharField(max_length=255)
    origin_id = models.IntegerField()

    repeat_frequency = models.IntegerField(null=True, blank=True, choices=Frequency.choices)
    reminders = ArrayField(models.PositiveIntegerField(), size=10, null=True, blank=True)  # Max 10 reminders

    NOTIFICATION_DATA_FIELDS = (('id', int),
                                ('title', str),
                                ('description', str),
                                ('origin_name', str, 'Related model name for the event'),
                                ('origin_id', int, 'Related model ID for the event'),
                                ('schedule_origin_name', str, 'Related model name for the schedule'),
                                ('schedule_origin_id', int, 'Related model ID for the schedule'),
                                ('start_date', datetime),
                                ('end_date', datetime))

    @property
    def notification_data(self):
        return dict(id=self.id,
                    title=self.title,
                    description=self.description,
                    origin_name=self.origin_name,
                    origin_id=self.origin_id,
                    schedule_origin_name=self.schedule.origin_name,
                    schedule_origin_id=self.schedule.origin_id,
                    start_date=self.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    end_date=self.end_date.strftime('%Y-%m-%d %H:%M:%S'))

    def notify_reminders(self, action: NotificationObject.Action, timestamp: datetime.datetime, message: str):
        data = locals()
        data.pop('self')

        return self.notification_channel.notify(**data)

    def notify_start(self, action: NotificationObject.Action, timestamp: datetime.datetime, message: str):
        data = locals()
        data.pop('self')

        return self.notification_channel.notify(**data)

    def notify_end(self, action: NotificationObject.Action, timestamp: datetime.datetime, message: str):
        data = locals()
        data.pop('self')

        return self.notification_channel.notify(**data)

    def _get_cron_from_date(self, date: datetime.datetime):
        date = date.astimezone(timezone.now().tzinfo)
        freq = self.Frequency

        if self.repeat_frequency == freq.DAILY:
            schedule = crontab(minute=date.minute, hour=date.hour)
        elif self.repeat_frequency == freq.WEEKLY:
            schedule = crontab(minute=date.minute,
                               hour=date.hour,
                               day_of_week=str(date.weekday()))
        elif self.repeat_frequency == freq.MONTHLY:
            schedule = crontab(minute=date.minute,
                               hour=date.hour,
                               day_of_month=date.day)
        elif self.repeat_frequency == freq.YEARLY:
            schedule = crontab(minute=date.minute,
                               hour=date.hour,
                               day_of_month=date.day,
                               month_of_year=date.month)
        else:
            schedule = None

        return schedule

    @property
    def next_start_date(self) -> datetime.datetime:
        if timezone.now() < self.start_date:
            return self.start_date
        else:
            return timezone.now() + self._get_cron_from_date(self.start_date).remaining_estimate(timezone.now())

    @property
    def next_end_date(self) -> datetime.datetime:
        if timezone.now() < self.end_date:
            return self.end_date
        else:
            return timezone.now() + self._get_cron_from_date(self.end_date).remaining_estimate(timezone.now())

    def regenerate_notifications(self):
        """Regenerate notifications for the event"""
        if not self.repeat_frequency and timezone.now() > self.start_date:
            return

        self.notification_channel.notificationobject_set.filter(timestamp__gte=timezone.now()).all().delete()

        if self.reminders:
            for reminder in self.reminders:
                cron = self._get_cron_from_date(self.start_date - datetime.timedelta(seconds=reminder))
                if cron:
                    reminder = timezone.now() - cron.remaining_estimate(timezone.now())
                    self.notify_reminders(NotificationObject.Action.UPDATED,
                                          timestamp=reminder,
                                          message=f"Reminder for upcoming event: {self.title}")

        if self.next_start_date:
            self.notify_start(NotificationObject.Action.CREATED,
                              timestamp=self.next_start_date,
                              message=f"Event started: {self.title}")

        if self.next_end_date:
            self.notify_end(NotificationObject.Action.CREATED,
                            timestamp=self.next_end_date,
                            message=f"Event ended: {self.title}")

    def clean(self):
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError('Start date is greater than end date')

        if self.reminders:
            if len(set(self.reminders)) < len(self.reminders):
                raise ValidationError("Reminders can't have duplicates")

    @classmethod
    def post_save(cls, instance, created, update_fields: list[str] = None, *args, **kwargs):
        if instance.repeat_frequency:
            cron_data = dict()
            if instance.repeat_frequency == instance.Frequency.WEEKLY:
                cron_data['day_of_week'] = str(instance.end_date.weekday())

            elif instance.repeat_frequency == instance.Frequency.MONTHLY:
                cron_data['day_of_month'] = instance.end_date.day

            elif instance.repeat_frequency == instance.Frequency.YEARLY:
                cron_data['month_of_year'] = instance.end_date.month
                cron_data['day_of_month'] = instance.end_date.day

            schedule = CrontabSchedule.objects.get_or_create(minute=instance.end_date.minute,
                                                             hour=instance.end_date.hour,
                                                             **cron_data)

            if not created:
                task = PeriodicTask.objects.get(name=f"schedule_event_{instance.id}")
                if task.crontab != schedule[0]:
                    task.crontab = schedule[0]
                    task.save()

                return

            periodic_task = PeriodicTask.objects.create(name=f"schedule_event_{instance.id}",
                                                        task="schedule.tasks.event_notify",
                                                        kwargs=json.dumps(dict(event_id=instance.id)),
                                                        crontab=schedule[0],
                                                        one_off=bool(not instance.reminders))
            periodic_task.full_clean()
            periodic_task.save()

            instance.regenerate_notifications()

        else:
            if not created:
                PeriodicTask.objects.filter(name=f"schedule_event_{instance.id}").delete()

        if not created:
            if update_fields and any([x in update_fields for x in ['end_date', 'start_date', 'repeat_frequency']]):
                instance.regenerate_notifications()

    @classmethod  # Delete reminders
    def post_delete(cls, instance, *args, **kwargs):
        PeriodicTask.objects.filter(name=f"schedule_event_{instance.id}").delete()


post_save.connect(ScheduleEvent.post_save, ScheduleEvent)
post_delete.connect(ScheduleEvent.post_delete, ScheduleEvent)


class ScheduleSubscription(BaseModel):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='schedule_subscription_schedule')
    target = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='schedule_subscription_target')

    def clean(self):
        if self.schedule == self.target:
            raise ValidationError('Schedule cannot be the same as the target')

    class Meta:
        unique_together = ('schedule', 'target')
