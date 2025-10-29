import datetime
import json

import pgtrigger
from celery.schedules import crontab
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import post_save, post_delete, pre_delete
from django.utils import timezone
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from rest_framework.exceptions import ValidationError

from flowback.common.models import BaseModel
from django.utils.translation import gettext_lazy as _

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

        return event

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
    end_date = models.DateTimeField(null=True, blank=True)
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

            if not all([assignee.group == group for assignee in self.assignees.all()]):
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
        if not self.repeat_frequency and self.end_date and timezone.now() > self.end_date:
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
        if not created and (update_fields and 'tag' in update_fields):
            ScheduleEventUserData.objects.filter(event=instance, locked=False).delete()

        # Notification subscription management
        if created or (update_fields and 'repeat_frequency' in update_fields):
            subscribers = ScheduleTagSubscription.objects.filter(schedule_subscription__schedule=instance.schedule,
                                                                 schedule_tag=instance.tag)

            for subscriber in subscribers:
                instance.subscribe(user=subscriber.schedule_subscription.user,
                                   tags=["start", "end"],
                                   reminders=((*instance.reminders), None))

                ScheduleEventUserData.objects.create(event=instance,
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
                    task.start_date = instance.start_date
                    task.crontab = cron_schedule
                    task.save()

                return

            periodic_task = PeriodicTask.objects.create(name=f"schedule_event_{instance.id}",
                                                        task="schedule.tasks.event_notify",
                                                        kwargs=json.dumps(dict(event_id=instance.id)),
                                                        crontab=cron_schedule,
                                                        start_time=instance.start_date)
            periodic_task.full_clean()
            periodic_task.save()

            instance.regenerate_notifications()

        if not created:
            if update_fields and any([x in update_fields for x in ['end_date', 'start_date', 'repeat_frequency']]):
                instance.regenerate_notifications()


post_save.connect(ScheduleEvent.post_save, ScheduleEvent)


class ScheduleEventUserData(BaseModel):
    event = models.ForeignKey(ScheduleEvent, on_delete=models.CASCADE)
    subscription = models.ForeignKey('schedule.ScheduleSubscription', on_delete=models.CASCADE)
    tags = ArrayField(base_field=models.CharField(max_length=100), size=10, null=True, blank=True,
                      help_text="A list of user-defined tags")
    locked = models.BooleanField(default=True, help_text="If set to true and user unsubscribes from the tag related "
                                                         "to the event, the event will remain subscribed.")


class ScheduleTagSubscription(BaseModel):
    schedule_subscription = models.ForeignKey('schedule.ScheduleSubscription', on_delete=models.CASCADE)
    schedule_tag = models.ForeignKey(ScheduleTag, on_delete=models.CASCADE)
    reminders = ArrayField(models.PositiveIntegerField(), size=10, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['schedule_subscription', 'schedule_tag'],
                                    name='unique_schedule_tag_subscription'),
            pgtrigger.Protect(name='prevent_update_schedule_tag_subscription',
                              operation=pgtrigger.Update)
        ]

    @classmethod
    def post_save(cls, instance, created, *args, **kwargs):
        if not created:
            return

        events = instance.schedule_tag.scheduleevent_set.filter(Q(start_date__gte=timezone.now())
                                                                | Q(end_date__isnull=True)
                                                                | Q(end_date__gt=timezone.now()), active=True)

        with transaction.atomic():
            for event in events:
                ScheduleEventUserData.objects.get_or_create(event=event,
                                                            subscription=instance.schedule_subscription,
                                                            locked=False)

                event.notification_channel.subscribe(user=instance.schedule_subscription.user,
                                                     tags=["start", "end"],
                                                     reminders=None if not instance.reminders
                                                     else ((*instance.reminders), None))

    def delete_user_events(self, include_locked: bool = False, user_tag: str | None = None):
        filters = dict()
        if not include_locked:
            filters['scheduleeventsubscription__locked'] = False

        if user_tag:
            filters['scheduleeventsubscription__user'] = self.schedule_subscription.user
            filters['scheduleeventsubscription__tag'] = user_tag

        events = ScheduleEvent.objects.filter(
            schedule=self.schedule_subscription.schedule,
            tag=self.schedule_tag,
            scheduleeventsubscription__subscription__user=self.schedule_subscription.user,
            **filters)

        with transaction.atomic():
            ScheduleEventUserData.objects.filter(event__in=events, subscription=self.schedule_subscription).delete()

            # Unsubscribes user
            for event in events:
                event.notification_channel.unsubscribe(user=self.schedule_subscription.user)

    @classmethod
    def pre_delete(cls, instance, *args, **kwargs):
        instance.delete_user_events()


post_save.connect(ScheduleTagSubscription.post_save, ScheduleTagSubscription)
pre_delete.connect(ScheduleTagSubscription.pre_delete, ScheduleTagSubscription)


class ScheduleSubscription(BaseModel):
    subscribe_to_new_notification_tags = models.BooleanField(default=False, blank=True)
    notification_tags = models.ManyToManyField(ScheduleTag, blank=True, through=ScheduleTagSubscription)

    user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='schedule_subscription_user',
                             null=True)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='schedule_subscription_schedule')

    class Meta:
        unique_together = ('user', 'schedule')

    def delete_tag_subscriptions(self,
                                 tag: str | None,
                                 user_tag: str | None = None,
                                 include_locked: bool = False) -> None:
        """
        Deletes all notifications and tag subscriptions for the user and schedule.
        :param tag: Relevant tags to target, leave empty to delete all notification subscriptions.
        :param user_tag: Relevant user tags to target, leave empty to delete all notification subscriptions.
        :param include_locked: Whether to include user-locked events or not.
        :return: None
        """
        with transaction.atomic():
            if not tag and not user_tag:  # Delete all subscriptions
                ScheduleTagSubscription.objects.filter(schedule_subscription=self).delete()

            if tag:  # Delete tag & (tag, user_tag) subscriptions
                tag = ScheduleTag.objects.get(schedule=self.schedule, name=tag)
                ScheduleTagSubscription.objects.get(
                    schedule_subscription=self,
                    schedule_tag_id=tag
                ).delete_user_events(include_locked=include_locked,
                                     user_tag=user_tag)

            if user_tag:  # Delete user_tag subscriptions
                subscriptions = ScheduleTagSubscription.objects.filter(schedule_subscription=self)

                for sub in subscriptions:
                    sub.delete_user_events(include_locked=include_locked,
                                           user_tag=user_tag)


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
