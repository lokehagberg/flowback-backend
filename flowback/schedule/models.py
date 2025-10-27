import datetime
import json

import pgtrigger
from celery.schedules import crontab
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.db.models.signals import post_save, post_delete
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from rest_framework.exceptions import ValidationError

from flowback.common.models import BaseModel
from django.utils.translation import gettext_lazy as _

from flowback.group.models import GroupUser
from flowback.notification.models import NotifiableModel, NotificationObject, NotificationSubscription


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

    # Create Event
    def create_event(self, *,
                     title: str,
                     description: str = None,
                     start_date: datetime,
                     end_date: datetime = None,
                     created_by=None,
                     tag: str = None,
                     assignees: list[int] = None,
                     meeting_link: str = None,
                     repeat_frequency: int = None):
        tag = ScheduleTag.objects.get(schedule=self, name=tag)
        event = ScheduleEvent(title=title,
                              description=description,
                              start_date=start_date,
                              end_date=end_date,
                              schedule=self,
                              created_by=created_by,
                              tag=tag,
                              assignees=assignees,
                              meeting_link=meeting_link,
                              repeat_frequency=repeat_frequency)

        event.full_clean()
        event.save()

    # Subscribe (incl. unsubscribe, which deletes the subscription)
    def subscribe(self, user, tags: dict[str, list[int]] = None):
        """
        Subscribe/Unsubscribe to a schedule.
        :param user: A user object
        :param tags: A dictionary in the format of {tag_name<str>: [reminders<int>, ...]}.
            If set to None, it unsubscribes the user from the schedule.
        :return: ScheduleSubscription object (or None if unsubscribed)
        """
        if not tags:
            ScheduleSubscription.objects.filter(schedule=self, user=user).delete()
            return None

        with transaction.atomic():
            subscription = ScheduleSubscription(user=user, schedule=self)
            subscription.full_clean()
            subscription.save()

            for tag, reminders in tags.items():
                schedule_tag = ScheduleTag.objects.get(schedule=self, name=tag)
                subscription.notification_tags.add(schedule_tag, through_defaults=dict(reminders=reminders))

        return subscription

    @classmethod
    def post_save(cls, instance, created, *args, **kwargs):
        if not created:
            return

        default_tag = ScheduleTag.objects.create(name='default')
        instance.default_tag = default_tag
        instance.save()


class ScheduleTag(BaseModel, NotifiableModel):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    @classmethod
    def post_save(cls, instance, created, *args, **kwargs):
        if not created:
            return

        subscriptions = ScheduleSubscription.objects.filter(schedule=instance.schedule,
                                                            subscribe_to_new_notification_tags=True)

        for sub in subscriptions:
            ScheduleTagSubscription.objects.get_or_create(schedule_subscription=sub,
                                                          schedule_tag=instance)


post_save.connect(ScheduleTag.post_save, ScheduleTag)


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
    end_date = models.DateTimeField(null=True, blank=True)  # TODO end date should be required?
    active = models.BooleanField(default=True)
    tag = models.ForeignKey(ScheduleTag, on_delete=models.CASCADE, null=True, blank=True)

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

    def clean(self, *args, **kwargs):
        # Manual management of getting group from created_by
        if self.assignees:
            model = self.content_type.model
            group = None

            if not model in ['group', 'poll', 'workgroup']:
                raise ValidationError("Assignees can only be assigned to events created by a group.")

            match model:
                case 'group':
                    group = self.created_by
                case _:
                    group = self.created_by.group

            assignee_ids = list(self.assignees.values_list('id', flat=True))
            assignees = GroupUser.objects.filter(group=group, id__in=assignee_ids)
            if self.assignees.count() != len(assignees):
                raise ValidationError("Not all group users are assignable to this event.")

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

    @classmethod
    def post_save(cls, instance, created, update_fields: list[str] = None, *args, **kwargs):
        # Notification subscription management
        if created or (update_fields and 'repeat_frequency' in update_fields):
            subscribers = ScheduleTagSubscription.objects.filter(schedule_subscription__schedule=instance.schedule,
                                                                 schedule_tag=instance.tag)

            for subscriber in subscribers:
                instance.subscribe(user=subscriber.schedule_subscription.user,
                                   tags=["start", "end"],
                                   reminders=subscriber.reminders)

                ScheduleEventSubscription.objects.create(event=instance,
                                                         subscription=subscriber.schedule_subscription,
                                                         locked=False)

        # Repeat Frequency and notification management
        if instance.repeat_frequency:
            cron_data = dict()
            if instance.repeat_frequency == instance.Frequency.WEEKLY:
                cron_data['day_of_week'] = str(instance.end_date.weekday())

            elif instance.repeat_frequency == instance.Frequency.MONTHLY:
                cron_data['day_of_month'] = instance.end_date.day

            elif instance.repeat_frequency == instance.Frequency.YEARLY:
                cron_data['month_of_year'] = instance.end_date.month
                cron_data['day_of_month'] = instance.end_date.day

            cron_schedule = CrontabSchedule.objects.get_or_create(minute=instance.end_date.minute,
                                                                  hour=instance.end_date.hour,
                                                                  **cron_data)[0]

            # If not created, update the instance task with a new crontab schedule
            task = PeriodicTask.objects.filter(name=f"schedule_event_{instance.id}").first()
            if not created and not task:
                if task.crontab != cron_schedule:
                    task.crontab = cron_schedule
                    task.save()

                return

            periodic_task = PeriodicTask.objects.create(name=f"schedule_event_{instance.id}",
                                                        task="schedule.tasks.event_notify",
                                                        kwargs=json.dumps(dict(event_id=instance.id)),
                                                        crontab=cron_schedule)
            periodic_task.full_clean()
            periodic_task.save()

            instance.regenerate_notifications()

        if not created:
            if update_fields and any([x in update_fields for x in ['end_date', 'start_date', 'repeat_frequency']]):
                instance.regenerate_notifications()


post_save.connect(ScheduleEvent.post_save, ScheduleEvent)


class ScheduleEventSubscription(BaseModel):
    event = models.ForeignKey(ScheduleEvent, on_delete=models.CASCADE)
    subscription = models.ForeignKey('schedule.ScheduleSubscription', on_delete=models.CASCADE)
    tags = ArrayField(base_field=models.CharField(max_length=100), size=10, null=True, blank=True,
                      help_text="A list of user-defined tags")
    locked = models.BooleanField(default=True, help_text="If set to true and user unsubscribes from the tag related "
                                                         "to the event, the event will remain subscribed.")


# TODO post_save should auto-subscribe any recurring and future event subscriptions
#   if reminders is None, notification subscriptions will be subscribed without reminders
#   Make sure to think of update operations
class ScheduleTagSubscription(BaseModel):
    schedule_subscription = models.ForeignKey('schedule.ScheduleSubscription', on_delete=models.CASCADE)
    schedule_tag = models.ForeignKey(ScheduleTag, on_delete=models.CASCADE)
    reminders = ArrayField(models.PositiveIntegerField(), size=10, null=True, blank=True)

    @classmethod
    def post_delete(self, instance, *args, **kwargs):
        content_type = ContentType.objects.get_for_model(ScheduleEvent)
        object_ids = ScheduleEvent.objects.filter(
            schedule=instance.schedule,
            tag=instance.schedule_tag,
            scheduleeventsubscription__subscription__user=instance.schedule_subscription.user,
            scheduleeventsubscription__locked=False,
        ).values_list('id', flat=True)

        NotificationSubscription.objects.filter(content_type=content_type,
                                                object_ids=object_ids,
                                                user=instance.schedule_subscription.user).delete()


post_delete.connect(ScheduleTagSubscription.post_delete, ScheduleTagSubscription)


# TODO post_delete should remove all schedule event notification subscriptions
class ScheduleSubscription(BaseModel):
    subscribe_to_new_notification_tags = models.BooleanField(default=False, blank=True)
    notification_tags = models.ManyToManyField(ScheduleTag, blank=True, through=ScheduleTagSubscription)

    user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='schedule_subscription_user',
                             null=True)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='schedule_subscription_schedule')

    class Meta:
        unique_together = ('user', 'schedule')

    # TODO update code with new fields
    def delete_all_notification_subscriptions(self,
                                              tags: str | None,
                                              user_tags: list[str] | None = None,
                                              include_locked: bool = False):
        """
        Deletes all notifications and tag subscriptions for the user and schedule.
        :param tags: Relevant tags to target, leave empty to delete all notification subscriptions.
        :param reminders: Specific reminder pattern to target, leave empty to ignore.
        :return: Total number of deleted notification subscriptions.
        """
        filters = dict()
        with transaction.atomic():
            # Delete tag subscriptions, and if tags exist, add filters for the next step
            if tags:
                tags = ScheduleTag.objects.filter(schedule=self.schedule,
                                                  name__in=tags).values_list('id',
                                                                             flat=True)
                filters['scheduletag__id__in'] = list(tags)

                ScheduleTagSubscription.objects.filter(schedule_tag__id__in=tags).delete()

            else:
                ScheduleTagSubscription.objects.filter(schedule_subscription=self).delete()

            if reminders:
                filters['scheduletagsubscription__reminders'] = reminders

            content_type = ContentType.objects.get_for_model(ScheduleEvent)
            object_ids = ScheduleEvent.objects.filter(schedule=self.schedule,
                                                      schedulesubscription__user=self.user,
                                                      **filters).values_list('id', flat=True)

            subs = NotificationSubscription.objects.filter(content_type=content_type,
                                                           object_ids=object_ids,
                                                           user=self.user)

            total_subs = subs.count()
            subs.delete()

            return total_subs


def generate_schedule(sender, instance, created, *args, **kwargs):
    if created and issubclass(sender, ScheduleModel):
        Schedule.objects.create(created_by=instance)


class ScheduleModel(models.Model):
    schedule_relations = GenericRelation(Schedule)

    class Meta:
        abstract = True

    @property
    def schedule(self):
        return self.schedule_relations.first()

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        models.signals.post_save.connect(generate_schedule, sender=cls)
