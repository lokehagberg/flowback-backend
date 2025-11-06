import inspect
import re
from datetime import timedelta, datetime
from inspect import getfullargspec, isclass

from django.db import models
from django.db.models import F, Q, Sum, ExpressionWrapper
from django.db.models.fields.files import ImageFieldFile
from django.db.models.signals import post_save
from django.utils import timezone

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from rest_framework.exceptions import ValidationError
from tree_queries.models import TreeNode

from flowback.common.models import BaseModel


# NotificationObject is created containing data for each occurrence
class NotificationObject(BaseModel):
    class Action(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        UPDATED = 'UPDATED', 'Updated'
        DELETED = 'DELETED', 'Deleted'
        INFO = 'INFO', 'Info'
        WARNING = 'WARNING', 'Warning'
        ERROR = 'ERROR', 'Error'

    action = models.CharField(choices=Action.choices)
    message = models.TextField(max_length=2000)
    tag = models.CharField(max_length=255, help_text='Tag of the notification')
    data = models.JSONField(null=True, blank=True)  # Suggested to store relevant data for user
    timestamp = models.DateTimeField(default=timezone.now)
    channel = models.ForeignKey('notification.NotificationChannel', on_delete=models.CASCADE)

    def clean(self):
        if self.tag not in self.channel.tags:
            raise ValidationError('Invalid tag, must be in channel tags')

        if self.data and any([isinstance(v, ImageFieldFile) for v in self.data.values()]):
            raise TypeError('Data must be a dictionary of primitive types')

    @classmethod
    def post_save(cls, instance, created, *args, **kwargs):
        """
        Creates Notification for users on save for the given tag
        If NotificationSubscriptionTag has reminders, creates a Notification for each reminder
        """

        subscription_filters = dict()
        subscription_q_filters = []
        exclude_subscription_filters = dict()
        exclude_subscription_q_filters = []

        if hasattr(instance, 'subscription_filters'):
            subscription_filters = instance.subscription_filters

        if hasattr(instance, 'subscription_q_filters'):
            subscription_q_filters = instance.subscription_q_filters

        if hasattr(instance, 'subscription_filters'):
            exclude_subscription_filters = instance.exclude_subscription_filters

        if hasattr(instance, 'subscription_q_filters'):
            exclude_subscription_q_filters = instance.exclude_subscription_q_filters

        if created:
            subscribers = NotificationSubscription.objects.filter(
                *subscription_q_filters,
                channel=instance.channel,
                notificationsubscriptiontag__name=instance.tag,
                **subscription_filters
            ).exclude(
                *exclude_subscription_q_filters,
                **exclude_subscription_filters
            ).annotate(reminders=F('notificationsubscriptiontag__reminders'))

            notifications = []
            for subscriber in subscribers:
                if subscriber.reminders:
                    for i in subscriber.reminders:
                        notifications.append(Notification(user=subscriber.user,
                                                          notification_object=instance,
                                                          reminder=i))

                notifications.append(Notification(user=subscriber.user, notification_object=instance))

            Notification.objects.bulk_create(notifications)


post_save.connect(NotificationObject.post_save, NotificationObject)


# Notification is created for every user subscribed to a channel,
# with a NotificationObject attached to it containing the data
class Notification(BaseModel):
    user = models.ForeignKey('user.User', on_delete=models.CASCADE)
    notification_object = models.ForeignKey("notification.NotificationObject", on_delete=models.CASCADE)
    read = models.BooleanField(default=False)

    reminder = models.IntegerField(default=0, blank=True)

    class Meta:
        unique_together = ('user', 'notification_object', 'reminder')


# Notification Subscription allows users to subscribe to the NotificationChannel, to get Notifications for themselves
class NotificationSubscription(BaseModel):
    user = models.ForeignKey('user.User', on_delete=models.CASCADE)
    channel = models.ForeignKey('notification.NotificationChannel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'channel')


class NotificationSubscriptionTag(BaseModel):
    subscription = models.ForeignKey('notification.NotificationSubscription', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    reminders = ArrayField(models.PositiveIntegerField(), help_text='Reminder times for the given tag', null=True, blank=True)

    class Meta:
        unique_together = ('subscription', 'name')

    @staticmethod
    def post_save(sender, instance, created, update_fields, *args, **kwargs):
        update_fields = update_fields or []

        if update_fields:
            if not all(isinstance(field, str) for field in update_fields):
                update_fields = [field.name for field in update_fields]

        # If there are upcoming reminders, remove all and replace with new ones
        if (created and instance.reminders is not None) or 'reminders' in update_fields:
            Notification.objects.filter(
                ~Q(reminder=0),
                user=instance.schedule_user.user,
                notification_object__tag=instance.name
            ).annotate(ts=ExpressionWrapper(F('notification_object__timestamp') - F('reminder') * timedelta(seconds=1),
                              output_field=models.DateTimeField())
                       ).filter(ts__lte=timezone.now()).delete()

            notification_objects = NotificationObject.objects.filter(tag=instance.name,
                                                                     notification__user=instance.schedule_user.user)

            # Add new reminders if any
            if instance.reminders and len(instance.reminders) > 0:
                notifications = []
                for notification_object in notification_objects:
                    for i in instance.reminders:
                        if notification_object.timestamp - timedelta(seconds=i) > timezone.now():
                            notifications.append(Notification(user=instance.schedule_user.user,
                                                              notification_object=notification_object,
                                                              reminder=i))

                Notification.objects.bulk_create(notifications)

    def clean(self):
        if not self.name in self.subscription.channel.tags:
            raise ValidationError(f'Tag does not exist for NotificationChannel {self.subscription.channel.name}. '
                                  f'Following options are available: {", ".join(self.subscription.channel.tags)}')


post_save.connect(NotificationSubscriptionTag.post_save, NotificationSubscriptionTag)


# For any model using Notification, it is recommended to use post_save to create a NotificationChannel object
class NotificationChannel(BaseModel, TreeNode):
    Action = NotificationObject.Action

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    @property
    def tags(self) -> list | None:
        """
        A list containing notification tags.
        """
        return [tag.replace('notify_', '') for tag in dir(self.content_object) if tag.startswith('notify_')]

    def get_tag_fields(self, tag: str) -> list | None:
        """
        A list containing notification tag fields from the inheriting model.
        :param tag: Name of the notification tag
        :return:
        """

        # Get functions that starts with 'notify_'
        tag_func_names = [tag_func_name for tag_func_name in dir(self.content_object) if
                          tag_func_name.startswith('notify_')]

        # Get attributes from the function related to tag and returns field names
        if f'notify_{tag}' in tag_func_names:
            excluded_fields = ['self', 'user_filters', 'user_q_filters', 'message', 'action']
            tag_fields = list(*getfullargspec(getattr(self.content_object, f'notify_{tag}'))[0])
            tag_fields = [tag_field for tag_field in tag_fields
                          if not (tag_field in excluded_fields
                                  or tag_field.startswith('_', ''))]

            return tag_fields

        return None

    def get_subscriber(self, user) -> NotificationSubscription | None:
        try:
            return NotificationSubscription.objects.get(channel=self, user=user)

        except NotificationSubscription.DoesNotExist:
            return None

    # Grabs the notification_data property from content_object (if any)
    @property
    def data(self) -> dict | None:
        if self.content_object.notification_data is not None:
            data = self.content_object.notification_data

            # Patch to fix django's immaculate ImageFieldFile serialization for JSONField
            for k, v in data.items():
                if isinstance(v, ImageFieldFile):
                    if not v:
                        data[k] = None
                    else:
                        data[k] = v.url

            return data

        else:
            return None

    @property
    def name(self) -> str:
        return self.content_object.__class__.__name__.lower()

    def notify(self,
               action: NotificationObject.Action,
               message: str,
               tag: str = None,
               timestamp: datetime = None,
               subscription_filters: dict = None,
               subscription_q_filters: list[Q] = None,
               exclude_subscription_filters: dict = None,
               exclude_subscription_q_filters: list[Q] = None,
               **data) -> NotificationObject:
        """
        Creates a new notification. If called by a 'notify_*' function,
        args prefixed with '_' won't be used for documentation.

        Example usage within a model:

        .. code-block:: python

        def notify_upvote(self, action: NotificationObject.Action, user: User):
                self.channel.notify(**locals())

        :param action: Check NotificationObject.Action for more information
        :param message: A text containing the message.
        :param tag: Optional tag for the notification. If not provided,
         the tag will take the calling function name (without the 'notify_' prefix) if it exists, otherwise
         it raises an error.
        :param timestamp: Timestamp when this notification becomes active. Defaults to timezone.now().
        :param data: Additional data to pass to the notification. Note that it'll always pop 'self' from the data to work with locals().
        :param subscription_filters: List of NotificationSubscription filters to pass onto the delivery of notifications.
        :param subscription_q_filters: List of NotificationSubscription Q filters to pass onto the delivery of notifications.
        """
        if "self" in data.items():
            data.pop('self')  # Always remove 'self' from data

        source = inspect.stack()[1].function
        if source.startswith('notify_') and not tag:
            tag = source.replace('notify_', '')

        elif not tag:
            raise ValidationError('Tag is required for non-notify functions')

        if self.content_object.notification_data is not None:
            data = data or {}
            data = data | self.content_object.notification_data

        # A patchwork for django image fields due to them returning <ImageFieldFile: None> when empty
        for k, v in data.items():
            if isinstance(v, ImageFieldFile):
                if not v:
                    data[k] = None
                else:
                    data[k] = v.url

        extra_fields = dict(timestamp=timestamp)  # Dict of fields that has defaults in NotificationObject model
        notification_object = NotificationObject(channel=self,
                                                 action=action,
                                                 message=message,
                                                 tag=tag,
                                                 data=data,
                                                 **{k: v for k, v in extra_fields.items() if v is not None})

        notification_object.subscription_filters = subscription_filters or {}
        notification_object.subscription_q_filters = subscription_q_filters or []
        notification_object.exclude_subscription_filters = exclude_subscription_filters or {}
        notification_object.exclude_subscription_q_filters = exclude_subscription_q_filters or []

        notification_object.full_clean()
        notification_object.save()

        return notification_object

    # TODO check if relevant, perhaps bulk delete is better
    def notification_object_delete(self,
                                   notification_object: NotificationObject | int):
        if isinstance(notification_object, NotificationObject):
            notification_object = notification_object.id

        NotificationObject.objects.get(channel_id=self.id, id=notification_object).delete()

    def shift(self,
              delta: int,
              **query_filters) -> None:
        """
        Shifts notifications using the delta (in seconds)
        :param delta: How much time to shift notifications (in seconds)
        :param query_filters: Filters to apply to the NotificationObject query.
        """
        filters = {key: val for key, val in query_filters.items() if val is not None}
        self.notificationobject_set.filter(**filters).update(timestamp=F('timestamp') + timedelta(seconds=delta))

    def __str__(self):
        return f"<NotificationChannel {self.id}> for {self.content_object.__str__()}"

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def subscribe(self, *, user,
                  tags: tuple[str] | list[str] = None,
                  reminders: tuple[None | tuple[int]] = None) -> NotificationSubscription | None:
        """
        Subscribes user to the channel.
        :param user: The subscriber
        :param tags: A tuple of tags to subscribe to.
        :param reminders: A tuple of reminders to subscribe to. If None, there will be no reminders.
          Reminders are expected to have field indexes correspond to the tag field indexed.
          Use None in the tuple to skip specific tag reminders.
        :return: A NotificationSubscription object if successful, or None if no tags are provided (unsubscribe).
        """

        # Delete subscription if no tags are present
        if not tags:
            try:
                NotificationSubscription.objects.get(user=user, channel=self).delete()

            except NotificationSubscription.DoesNotExist:
                pass

            return None

        subscription_tags: list[NotificationSubscriptionTag] = []
        for i, tag in enumerate(tags):
            if not tag in self.tags:
                raise ValidationError(f'Tag does not exist for {self.name}. '
                                      f'Following options are available: {", ".join(self.tags)}')

            rem = None
            if (reminders is not None
                    and len(reminders) >= i + 1
                    and reminders[i] is not None
                    and len(reminders[i]) <= 10):
                rem = reminders[i]

            if rem and any([r is not None and r == 0 for r in rem]):
                raise ValidationError('Reminders cannot be set to 0')

            subscription_tags.append(NotificationSubscriptionTag(name=tag, reminders=rem))

        subscription, created = NotificationSubscription.objects.update_or_create(user=user,
                                                                                  channel=self)

        NotificationSubscriptionTag.objects.filter(subscription=subscription).delete()
        for subscription_tag in subscription_tags:
            subscription_tag.subscription = subscription
            subscription_tag.full_clean()

        NotificationSubscriptionTag.objects.bulk_create(subscription_tags)

        return subscription

    def unsubscribe(self, *, user):
        self.subscribe(user=user)

    def unsubscribe_all(self, *, user):
        """
        Deletes all subscriptions for the given user, including related channels.
        """
        NotificationSubscription.objects.filter(channel__in=self.descendants(include_self=True)).delete()


def generate_notification_channel(sender, instance, created, *args, **kwargs):
    if created and issubclass(sender, NotifiableModel):
        parent_id = instance.related_notification_channel
        if isinstance(parent_id, NotificationChannel):
            parent_id = parent_id.id

        elif not (isinstance(parent_id, int) or parent_id is None):
            raise ValueError('related_notification_channel must be a NotificationChannel or an integer')

        NotificationChannel.objects.create(content_object=instance, parent_id=parent_id)


class NotifiableModel(models.Model):
    """
    A plugin for models, adding notification functionality to the model.
    To add tags, make 'notify_{tag_name}' functions within the class that calls
    on the models notification_channel.notify function.
    The fields for the function will be used for checks and documentation.
    """
    notification_channels = GenericRelation(NotificationChannel)
    NOTIFICATION_DATA_FIELDS: tuple[tuple[str, str] | tuple[str] | str] | None = None
    """A tuple containing information that'll be served from notification_data function, intended for documentation.
    **The tuple content should follow either of the following formats**: 
        > (key: str, type: str | class, description: str)
        > (key: str, type: str | class)
        > (key: str)
        > str
    """

    @property
    def notification_channel(self) -> NotificationChannel:
        return self.notification_channels.first()

    @property
    def notification_data(self) -> dict | None:
        return None

    @classmethod
    def notification_docs(cls) -> str:
        """
        Returns a string containing documentation for the model.
        """

        # Notification Data
        notification_data_doc = ""
        if cls.NOTIFICATION_DATA_FIELDS:
            notification_data_doc = (f"### Notification Data Fields\n"
                                     f"Data that'll be passed onto all notification tags related to this channel.\n"
                                     "| Field | Type | Description |\n"
                                     "| ----- | ---- | ----------- |\n")

            for field in cls.NOTIFICATION_DATA_FIELDS:
                if isinstance(field, tuple):
                    type_info = "undefined"
                    if len(field) > 1 and isclass(field[1]):
                        type_info = field[1].__name__

                    else:
                        type_info = field[1]

                    if len(field) == 3:
                        notification_data_doc += f"| {field[0]} | {type_info} | {field[2]} |\n"

                    if len(field) == 2:
                        notification_data_doc += f"| {field[0]} | {type_info} | |\n"

                    elif len(field) == 1:
                        notification_data_doc += f"| {field[0]} | | |\n"

                if isinstance(field, str):
                    notification_data_doc += f"| {field} | | |\n"

        # Notification Tags
        notification_tags_doc = ""
        tags = [(x[0].replace('notify_', ''), x[1])
                for x in inspect.getmembers(object=cls)
                if x[0].startswith('notify_')]

        if tags:
            notification_tags_doc = (f"### Notification Tags Fields\n"
                                     f"Data that'll be included (in addition to notification data) with every "
                                     f"Notification channel & tag pair related to this channel.\n\n")

            for tag, func in tags:
                docstring_data = {}
                notification_tags_doc += f"#### <ins>{tag}</ins>\n"
                if func.__doc__:
                    tag_description = None
                    pattern = r'(.*?)(?=:param|:return|$)'
                    match = re.search(pattern, func.__doc__, re.DOTALL)
                    if match:
                        # Get the description and remove extra whitespace
                        tag_description = match.group(1).strip()
                        # Replace multiple whitespaces with a single space
                        re.sub(r'\s+', ' ', tag_description)

                    notification_tags_doc += (f"{f'{tag_description}\n' if tag_description else ''}"
                                              "| Field | Type | Description |\n"
                                              "| ----- | ---- | ----------- |\n")

                    pattern = r':param (\w+):\ *(.*?)$'

                    # Process each line of the docstring
                    for line in func.__doc__.split('\n'):
                        line = line.strip()
                        match = re.match(pattern, line)

                        if match:
                            param_name = match.group(1)
                            description = match.group(2).strip()

                            if description:
                                docstring_data[param_name] = description

                else:
                    notification_tags_doc += ("| Field | Type | Description |\n"
                                              "| ----- | ---- | ----------- |\n")

                exclude_params = inspect.signature(NotificationChannel.notify).parameters.keys()
                for key, val in inspect.signature(func).parameters.items():
                    if key not in exclude_params and not key.startswith('_'):
                        notification_tags_doc += (f"| {key} "
                                                  f"| {val.annotation.__name__ if val.annotation.__name__ != '_empty' else 'undefined'} "
                                                  f"| {docstring_data.get(key, '')} |\n")

        docs = (f"### Subscription Information\n"
                f"Channel name: `{cls.__name__.lower()}`\n"
                f"{notification_data_doc}\n"
                f"{notification_tags_doc}")

        return docs

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        """
        The Constructor of NotifiableModel. Possible to pass in `related_notification_channel`
        as a kwarg (NotificationChannel or int).
        """
        self.related_notification_channel = kwargs.pop('related_notification_channel', None)
        super().__init__(*args, **kwargs)

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        models.signals.post_save.connect(generate_notification_channel, sender=cls)
