import datetime
import json

from celery.schedules import crontab
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from rest_framework.exceptions import ValidationError

from flowback.common.models import BaseModel
from django.utils.translation import gettext_lazy as _

from flowback.notification.models import NotifiableModel, NotificationObject


# TODO Migrate from origin_name and origin_id to content_type and object_id
# TODO find all origin name, origin id references and update them to use content_type and object_id
class Schedule(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    created_by = GenericForeignKey('content_type', 'object_id')

    default_tag = models.ForeignKey('schedule.ScheduleTag',
                                    on_delete=models.CASCADE,
                                    null=True,
                                    blank=True,
                                    related_name='default_tag')

    active = models.BooleanField(default=True)

    @classmethod
    def post_save(cls, instance, created, *args, **kwargs):
        if not created:
            return

        default_tag = ScheduleTag.objects.create(name='default')
        instance.default_tag = default_tag
        instance.save()


# TODO create a post_save method that automatically subscribes ScheduleSubscriptions who have subscribe_to_new_tags set to True
class ScheduleTag(BaseModel, NotifiableModel):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)


# TODO find all origin name, origin id references and update them to use content_type and object_id
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

    # Making assignees to User serves no purpose but to complicate queries
    assignees = models.ManyToManyField('group.GroupUser')
    meeting_link = models.URLField(null=True, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True)
    object_id = models.PositiveIntegerField(null=True)
    created_by = GenericForeignKey('content_type', 'object_id')

    repeat_frequency = models.IntegerField(null=True, blank=True, choices=Frequency.choices)

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
                    origin_name=self.content_type.model,
                    origin_id=self.object_id,
                    schedule_origin_name=self.schedule.content_type.model,
                    schedule_origin_id=self.schedule.object_id,
                    start_date=self.start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    end_date=self.end_date.strftime('%Y-%m-%d %H:%M:%S'))

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

        # if self.reminders:
        #     for reminder in self.reminders:
        #         cron = self._get_cron_from_date(self.start_date - datetime.timedelta(seconds=reminder))
        #         if cron:
        #             reminder = timezone.now() - cron.remaining_estimate(timezone.now())
        #             self.notify_reminders(NotificationObject.Action.UPDATED,
        #                                   timestamp=reminder,
        #                                   message=f"Reminder for upcoming event: {self.title}")

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

        # if self.reminders:
        #     if len(set(self.reminders)) < len(self.reminders):
        #         raise ValidationError("Reminders can't have duplicates")

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


class ScheduleTagSubscription(models.Model):
    schedule_subscription = models.ForeignKey('schedule.ScheduleSubscription', on_delete=models.CASCADE)
    schedule_tag = models.ForeignKey(ScheduleTag, on_delete=models.CASCADE)
    reminders = ArrayField(models.PositiveIntegerField(), size=10, null=True, blank=True)


class ScheduleSubscription(BaseModel):
    # TODO notification_tags allow users to auto-subscribe to any upcoming events with a specific tag
    subscribe_to_new_notification_tags = models.BooleanField(default=False, blank=True)
    notification_tags = models.ManyToManyField(ScheduleTag, blank=True, through=ScheduleTagSubscription)

    # TODO make not null, migrate from "schedule to schedule subscription" to "user to schedule subscription"
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='schedule_subscription_user', null=True)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='schedule_subscription_schedule')

    def clean(self):
        if self.schedule == self.target:
            raise ValidationError('Schedule cannot be the same as the target')

    class Meta:
        unique_together = ('user', 'schedule')
