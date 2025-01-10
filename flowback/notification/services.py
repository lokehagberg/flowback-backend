from datetime import datetime
from typing import Union

from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import NotificationChannel, NotificationObject, Notification, NotificationSubscription
from flowback.common.services import get_object


def notification_load_channel(*,
                              category: str,
                              sender_type: str,
                              sender_id: int,
                              create_if_not_exist: bool = True) -> NotificationChannel:
    if create_if_not_exist:
        channel, created = NotificationChannel.objects.get_or_create(category=category,
                                                                     sender_type=sender_type,
                                                                     sender_id=sender_id)

    else:
        channel = get_object(NotificationChannel, category=category, sender_type=sender_type, sender_id=sender_id)

    return channel


def notification_delete_channel(*, sender_type: str, sender_id: int, category: str = None) -> None:
    channels = NotificationChannel.objects.filter(sender_type=sender_type, sender_id=sender_id,
                                                  category=category).all()
    channels.delete()
    return


# tag (Action), sender_type (Name), sender_id (identifier)
# Notification subscription handled outside, notification management handled inside
def notification_create(*, action: str, category: str, sender_type: str, sender_id: int,
                        message: str, timestamp: datetime = None, related_id: int = None,
                        target_user_id: int = None) -> NotificationObject:
    channel = notification_load_channel(category=category, sender_type=sender_type, sender_id=sender_id)
    timestamp = timestamp or timezone.now()
    notification_object = NotificationObject.objects.create(channel=channel,
                                                            action=action,
                                                            message=message,
                                                            timestamp=timestamp,
                                                            related_id=related_id)

    if not target_user_id:
        subscribers = NotificationSubscription.objects.filter(channel=channel).all()
        Notification.objects.bulk_create([Notification(user=subscriber.user,
                                                       notification_object=notification_object)
                                          for subscriber in subscribers])

    else:
        notification = Notification(user_id=target_user_id,
                                    notification_object=notification_object)
        notification.full_clean()
        notification.save()

    return notification_object


def notification_shift(*, category: str, sender_type: str, sender_id: int,
                       related_id: int = None, timestamp: datetime = None,
                       timestamp__lt: datetime = None, timestamp__gt: datetime = None, action: str = None,
                       delta: timezone.timedelta):
    channel = notification_load_channel(category=category, sender_type=sender_type, sender_id=sender_id)
    timestamp = timestamp or timezone.now()
    filters = {a: b for a, b in dict(channel=channel, action=action, related_id=related_id, timestamp=timestamp,
                                     timestamp__lt=timestamp__lt, timestamp__gt=timestamp__gt).items() if b is not None}

    notifications = NotificationObject.objects.filter(**filters).update(timestamp=F('timestamp') + delta)


def notification_delete(*, category: str, sender_type: str, sender_id: int,
                        related_id: int = None, timestamp: datetime = None,
                        timestamp__lt: datetime = None, timestamp__gt: datetime = None, action: str = None):
    channel = notification_load_channel(category=category,
                                        sender_type=sender_type,
                                        sender_id=sender_id,
                                        create_if_not_exist=False)
    filters = {a: b for a, b in dict(channel=channel, action=action, related_id=related_id, timestamp=timestamp,
                                     timestamp__lt=timestamp__lt, timestamp__gt=timestamp__gt).items() if b is not None}
    notifications = NotificationObject.objects.filter(**filters)

    notifications.delete()


def notification_mark_read(*, fetched_by: int, notification_ids: list[int], read: bool) -> None:
    Notification.objects.filter(user_id=fetched_by, id__in=notification_ids).update(read=read)

def notification_channel_subscribe(*,
                                   user_id: int,
                                   category: str,
                                   sender_type: str,
                                   sender_id: int) -> NotificationSubscription:
    channel = notification_load_channel(category=category,
                                        sender_type=sender_type,
                                        sender_id=sender_id,
                                        create_if_not_exist=True)
    get_object(NotificationSubscription, user_id=user_id, channel=channel,
               error_message='User is already subscribed', reverse=True)
    subscription = NotificationSubscription(user_id=user_id, channel=channel)
    future_notifications = [Notification(user_id=user_id, notification_object=notification_object)
                            for notification_object
                            in NotificationObject.objects.filter(channel=channel,
                                                                 timestamp__gte=timezone.now()).all()]
    Notification.objects.bulk_create(future_notifications)
    subscription.full_clean()
    subscription.save()
    return subscription


def notification_channel_unsubscribe(*, user_id: int, category: str,
                                     sender_type: str, sender_id: int) -> None:
    channel = notification_load_channel(category=category,
                                        sender_type=sender_type,
                                        sender_id=sender_id,
                                        create_if_not_exist=False)
    subscription = get_object(NotificationSubscription, user_id=user_id, channel=channel)
    subscription.delete()
    Notification.objects.filter(user_id=user_id,
                                notification_object__channel=channel,
                                notification_object__timestamp__gte=timezone.now()).delete()
    return


class NotificationManager:
    class Action:
        create = 'create'
        update = 'update'
        delete = 'delete'
        info = 'info'

    def __init__(self, sender_type: str, possible_categories: list[str] = None):
        self.sender_type = sender_type
        self.possible_categories = possible_categories

    def category_is_possible(self, category: Union[str, list[str], set[str]], validation: bool = False):
        categories, failed_categories = [[]]*2
        if isinstance(category, set):
            categories = list(category)
        elif isinstance(category, str):
            categories = [category]

        if self.possible_categories:
            for category in categories:
                if category not in self.possible_categories:
                    failed_categories.append(category)

            if failed_categories:
                message = f'Category {", ".join(failed_categories)} is not in possible_categories, ' \
                          f'choices are: {", ".join(self.possible_categories)}'
                if validation:
                    raise ValidationError(message)
                else:
                    raise Exception(message)

        return categories

    def load_channel(self, *, sender_id: int, category: str):
        notification_load_channel(sender_type=self.sender_type, sender_id=sender_id, category=category)

    def is_subscribed(self, user_id: int, sender_id: int, category: int):
        return NotificationSubscription.objects.filter(user_id=user_id,
                                                       channel__sender_type=self.sender_type,
                                                       channel__sender_id=sender_id,
                                                       channel__category=category).exists()

    def delete_channel(self, *, sender_id: int, category: str = None):
        if category:
            self.category_is_possible(category)

        notification_delete_channel(sender_type=self.sender_type, sender_id=sender_id)

    def create(self, *, sender_id: int, action: str, category: str, message: str, timestamp: datetime = None,
               related_id: int = None, target_user_id: int = None):
        self.category_is_possible(category)

        notification_create(action=action, category=category, sender_type=self.sender_type, sender_id=sender_id,
                            message=message, timestamp=timestamp, related_id=related_id, target_user_id=target_user_id)

    def shift(self, *, category: str, sender_id: int, related_id: int = None, timestamp: datetime = None,
              timestamp__lt: datetime = None, timestamp__gt: datetime = None, action: str = None,
              delta: timezone.timedelta):
        self.category_is_possible(category)
        notification_shift(category=category, sender_type=self.sender_type, sender_id=sender_id, related_id=related_id,
                           timestamp=timestamp, timestamp__lt=timestamp__lt, timestamp__gt=timestamp__gt,
                           action=action, delta=delta)

    def delete(self, *, category: str, sender_id: int, related_id: int = None, action: str = None,
               timestamp: datetime = None, timestamp__lt: datetime = None, timestamp__gt: datetime = None):
        self.category_is_possible(category)

        notification_delete(category=category, sender_type=self.sender_type, sender_id=sender_id,
                            related_id=related_id, action=action, timestamp=timestamp,
                            timestamp__lt=timestamp__lt, timestamp__gt=timestamp__gt)

    def channel_subscribe(self, *, user_id: int, sender_id: int, category: Union[str, set[str], list[str]]):
        categories = self.category_is_possible(category, validation=True)

        for category in categories:
            notification_channel_subscribe(user_id=user_id, category=category, sender_type=self.sender_type,
                                           sender_id=sender_id)

    def channel_unsubscribe(self, *, user_id: int, sender_id: int, category):
        self.category_is_possible(category, validation=True)

        notification_channel_unsubscribe(user_id=user_id, category=category,
                                         sender_type=self.sender_type, sender_id=sender_id)
