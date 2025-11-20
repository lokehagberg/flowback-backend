import datetime
import json

import pgtrigger
from celery.events import event_exchange
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
        tag = ScheduleTag.objects.filter(schedule=self, name=tag).first()
        event = ScheduleEvent(title=title,
                              description=description,
                              start_date=start_date,
                              end_date=end_date,
                              schedule=self,
                              created_by=created_by,
                              tag=tag or self.default_tag,
                              meeting_link=meeting_link,
                              repeat_frequency=repeat_frequency)

        if assignees:
            event.assignees.add(*assignees)

        event.full_clean()
        event.save()

        return event

    def add_user(self, user):
        """
        Add user to schedule
        :param user: User to be added
        :return: ScheduleUser object
        """
        with transaction.atomic():
            schedule_user = ScheduleUser(user=user, schedule=self)
            schedule_user.full_clean()
            schedule_user.save()

            return schedule_user

    def remove_user(self, user) -> None:
        """
        Remove user from schedule
        :param user: User to be removed
        :return: None
        """
        with transaction.atomic():
            schedule_user = ScheduleUser.objects.filter(user=user, schedule=self).first()
            if schedule_user:
                schedule_user.delete()
            else:
                raise ValidationError("User is not added to this schedule.")

    def subscribe_new_tags(self, user, reminders: list[int] = None):
        """
        Subscribes to new tags
        :param user: User to subscribe
        :param reminders: A list of reminders (in seconds before the event begins)
        :return: ScheduleUser object
        """
        with transaction.atomic():
            schedule_user = ScheduleUser.objects.get(user=user, schedule=self)
            schedule_user.subscribe_to_new_notification_tags = True
            schedule_user.reminders = reminders
            schedule_user.save()
            return schedule_user

    def unsubscribe_new_tags(self, user):
        """
        Unsubscribes from new tags
        :param user: User to subscribe
        :return: ScheduleUser object
        """
        with transaction.atomic():
            schedule_user = ScheduleUser.objects.get(user=user, schedule=self)
            schedule_user.subscribe_to_new_notification_tags = False
            schedule_user.reminders = None
            schedule_user.save()
            return schedule_user

    def subscribe_tags(self, user, tag_ids: list, reminders: list[int] = None):
        """
        Subscribe to a schedule.
        :param user: A user object
        :param tag_ids: A list of tag id's
        :param reminders: A list of reminders (in seconds before the event begins)
        :return: ScheduleUser object
        """
        with transaction.atomic():
            schedule_user = ScheduleUser.objects.get(user=user, schedule=self)
            tags = ScheduleTag.objects.filter(schedule=self, id__in=tag_ids)
            for tag in tags:
                ScheduleTagSubscription.objects.update_or_create(schedule_user=schedule_user,
                                                                 schedule_tag=tag,
                                                                 defaults=dict(reminders=reminders))

    def unsubscribe_tags(self, user, tag_ids: list):
        """
        Unsubscribes from schedule tags.
        :param user: A user object
        :param tag_ids: A list of tag id's, leave empty to unsubscribe from all tags
        :return: ScheduleUser object
        """
        filters = {} if not tag_ids else dict(schedule_tag__id__in=tag_ids)

        with transaction.atomic():
            schedule_user = ScheduleUser.objects.get(user=user, schedule=self)
            tags = ScheduleTagSubscription.objects.filter(schedule_user=schedule_user,
                                                          **filters)

            if not tags.exists():
                raise ValidationError("User is not subscribed to any of the tags.")

            tags.delete()

    def subscribe_events(self, user, event_ids: list[int], user_tags: list[str], reminders: list[int], locked: bool):
        """
        Subscribe a user to a specified event with optional user tags and locked status.

        :param user: The user object who is subscribing to the event.
        :param event_id: ID of the event to subscribe to.
        :param user_tags: A list of user-defined tags.
        :param reminders: A list of reminders (in seconds before the event begins)
        :param locked: A boolean indicating whether the event subscription is locked
         (that is, not affected by tag subscribe/unsubscribe).
        :return: ScheduleEventUserData object
        """
        with transaction.atomic():
            events = ScheduleEvent.objects.filter(id__in=event_ids, schedule=self)
            for event in events:
                event.event_subscribe(user, user_tags, locked, reminders)

    def unsubscribe_events(self, user, event_ids: list[int]) -> None:
        """
        Unsubscribes a user from a specified event.

        :param user: The user object who is unsubscribing from the event.
        :param event_id: ID of the event to unsubscribe from.
        :return: None
        """
        with transaction.atomic():
            events = ScheduleEvent.objects.filter(id__in=event_ids, schedule=self)
            for event in events:
                event.event_unsubscribe(user)

    @classmethod
    def post_save(cls, instance, created, *args, **kwargs):
        if not created:
            return

        default_tag = ScheduleTag.objects.create(schedule=instance, name='default')
        instance.default_tag = default_tag
        instance.save()


post_save.connect(Schedule.post_save, Schedule)


class ScheduleTag(BaseModel, NotifiableModel):
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    @classmethod
    def post_save(cls, instance, created, *args, **kwargs):
        if not created:
            return

        subscriptions = ScheduleUser.objects.filter(schedule=instance.schedule,
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
    tag = models.ForeignKey(ScheduleTag, on_delete=models.CASCADE)

    # Making assignees to User serves no purpose but to complicate queries
    assignees = models.ManyToManyField('group.GroupUser')
    meeting_link = models.URLField(null=True, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
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
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError('Start date is greater than end date')

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
                    end_date=self.end_date.strftime('%Y-%m-%d %H:%M:%S') if self.end_date else None)

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
    def is_live(self) -> bool:
        """Returns whether the event has yet to begin or already begun"""
        return (self.active
                and self.start_date <= timezone.now() <= self.end_date
                if self.end_date else self.start_date <= timezone.now())

    @property
    def next_start_date(self) -> datetime.datetime:
        if timezone.now() < self.start_date:
            return self.start_date
        else:
            return timezone.now() + self._get_cron_from_date(self.start_date).remaining_estimate(timezone.now())

    @property
    def next_end_date(self) -> datetime.datetime | None:
        if not self.end_date:
            return None

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

    def event_subscribe(self, user,
                        user_tags: list[str] = None,
                        locked: bool = True,
                        reminders: list[int] = None):
        if not (self.active and self.is_live):
            return

        user_schedule = ScheduleUser.objects.get(schedule=self.schedule, user=user)
        ScheduleEventSubscription.objects.update_or_create(event=self,
                                                           schedule_user=user_schedule,
                                                           defaults=dict(tags=user_tags),
                                                           reminders=reminders,
                                                           locked=locked)

    def event_unsubscribe(self, user):
        with transaction.atomic():
            user_schedule = ScheduleUser.objects.get(schedule=self.schedule, user=user)
            ScheduleEventSubscription.objects.get(event=self, schedule_user=user_schedule).delete()

    @classmethod
    def post_save(cls, instance, created, update_fields: list[str] = None, *args, **kwargs):
        # Remove unrelated subscriptions and migrate new and existing subscribers to a new tag
        if not created and (update_fields and 'tag' in update_fields):
            schedule_event_user_datas = ScheduleEventSubscription.objects.filter(event=instance, locked=False)
            new_active_subscribers = ScheduleTagSubscription.objects.filter(schedule_tag=instance.tag)
            locked_users = ScheduleEventSubscription.objects.filter(event=instance,
                                                                    locked=True).values_list('schedule_user__user',
                                                                                             flat=True)

            # Delete subscriptions that are not in the new tag
            for i in schedule_event_user_datas:
                subscription_exists = new_active_subscribers.filter(schedule_user=i.schedule_user).exists()
                if not subscription_exists:
                    instance.event_unsubscribe(user=i.schedule_user.user)

            # Migrate subscriptions that are in the new tag (excluding users with locked event subscriptions)
            for i in new_active_subscribers.exclude(schedule_user__user__in=locked_users):
                instance.event_subscribe(user=i.schedule_user.user, reminders=i.reminders, locked=False)

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
            if task:
                if task.crontab != cron_schedule:
                    task.start_date = instance.start_date
                    task.crontab = cron_schedule
                    task.save()

            else:
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


class ScheduleEventSubscription(BaseModel):
    event = models.ForeignKey(ScheduleEvent, on_delete=models.CASCADE)
    schedule_user = models.ForeignKey('schedule.ScheduleUser', on_delete=models.CASCADE)
    reminders = ArrayField(models.PositiveIntegerField(), size=10, null=True, blank=True)
    tags = ArrayField(base_field=models.CharField(max_length=100), size=10, null=True, blank=True,
                      help_text="A list of user-defined tags")
    locked = models.BooleanField(default=True, help_text="If set to true and user unsubscribes from the tag related "
                                                         "to the event, the event will remain subscribed.")

    @classmethod
    def post_save(cls, instance, *args, **kwargs):
        instance.event.notification_channel.subscribe(user=instance.schedule_user.user,
                                                      tags=['start', 'end'],
                                                      reminders=(None if not instance.reminders
                                                                 else [instance.reminders, None]))

    @classmethod
    def pre_delete(cls, instance, *args, **kwargs):
        instance.event.notification_channel.unsubscribe(user=instance.schedule_user.user)


post_save.connect(ScheduleEventSubscription.post_save, ScheduleEventSubscription)
pre_delete.connect(ScheduleEventSubscription.pre_delete, ScheduleEventSubscription)


class ScheduleTagSubscription(BaseModel):
    schedule_user = models.ForeignKey('schedule.ScheduleUser', on_delete=models.CASCADE)
    schedule_tag = models.ForeignKey(ScheduleTag, on_delete=models.CASCADE)
    reminders = ArrayField(models.PositiveIntegerField(), size=10, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['schedule_user', 'schedule_tag'],
                                    name='unique_schedule_tag_subscription')
        ]
        triggers = [
            pgtrigger.Protect(name='prevent_update_schedule_tag_subscription',
                              operation=pgtrigger.Update)
        ]

    @classmethod
    def post_save(cls, instance, created, *args, **kwargs):
        events = instance.schedule_tag.scheduleevent_set.filter(Q(start_date__gte=timezone.now())
                                                                | Q(end_date__isnull=True)
                                                                | Q(end_date__gt=timezone.now()), active=True)

        with transaction.atomic():
            for event in events:
                event.event_subscribe(user=instance.schedule_user.user, locked=False, reminders=instance.reminders)

    def delete_user_events(self, include_locked: bool = False, user_tags: list[str] | None = None):
        filters = dict()
        if not include_locked:
            filters['scheduleeventsubscription__locked'] = False

        if user_tags:
            filters['scheduleeventsubscription__user'] = self.schedule_user.user
            filters['scheduleeventsubscription__tag__in'] = user_tags

        events = ScheduleEvent.objects.filter(
            schedule=self.schedule_user.schedule,
            tag=self.schedule_tag,
            scheduleeventsubscription__schedule_user__user=self.schedule_user.user,
            **filters)

        with transaction.atomic():
            for event in events:
                event.event_unsubscribe(user=self.schedule_user.user)

    @classmethod
    def pre_delete(cls, instance, *args, **kwargs):
        instance.delete_user_events()


post_save.connect(ScheduleTagSubscription.post_save, ScheduleTagSubscription)
pre_delete.connect(ScheduleTagSubscription.pre_delete, ScheduleTagSubscription)


# TODO add active status, should be possible to restore ScheduleUser when re-joining
class ScheduleUser(BaseModel):
    subscribe_to_new_notification_tags = models.BooleanField(default=False, blank=True)
    reminders = ArrayField(models.PositiveIntegerField(), size=10, null=True, blank=True)
    notification_tags = models.ManyToManyField(ScheduleTag, blank=True, through=ScheduleTagSubscription)

    user = models.ForeignKey('user.User', on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'schedule')

    def tag_unsubscribe(self,
                        tag_ids: list[int] | None,
                        include_locked: bool = False) -> None:
        """
        Deletes all notifications and tag subscriptions for the user and schedule.
        :param tag: Relevant tags to target, leave empty to delete all notification subscriptions.
        :param user_tag: Relevant user tags to target, leave empty to delete all notification subscriptions.
        :param include_locked: Whether to include user-locked events or not.
        :return: None
        """
        with transaction.atomic():
            ScheduleTagSubscription.objects.filter(schedule_user=self, schedule_tag__in=tag_ids).delete()

    def user_tag_unsubscribe(self,
                             user_tag_ids: list[int] | None,
                             include_locked: bool = False) -> None:
        """
        Deletes all notifications and tag subscriptions for the user and schedule.
        :param tag: Relevant tags to target, leave empty to delete all notification subscriptions.
        :param user_tag: Relevant user tags to target, leave empty to delete all notification subscriptions.
        :param include_locked: Whether to include user-locked events or not.
        :return: None
        """
        with transaction.atomic():
            tags = ScheduleEventSubscription.objects.filter(schedule_user=self)


def generate_schedule(sender, instance, created, *args, **kwargs):
    if created and issubclass(sender, ScheduleModel):
        Schedule.objects.create(created_by=instance)


# TODO implement ScheduleModel & views across the codebase, especially poll & tasks
class ScheduleModel(models.Model):
    schedule_relations = GenericRelation(Schedule, on_delete=models.CASCADE)

    class Meta:
        abstract = True

    @property
    def schedule(self):
        return self.schedule_relations.first()

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        models.signals.post_save.connect(generate_schedule, sender=cls)
