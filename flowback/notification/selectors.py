import django_filters
from django.utils import timezone

from .models import NotificationChannel, NotificationObject, Notification, NotificationSubscription
from ..user.models import User


class BaseNotificationFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('notification_object__timestamp',
                                                      'timestamp_asc'),
                                                     ('-notification_object__timestamp',
                                                      'timestamp_desc')))

    object_id = django_filters.NumberFilter(field_name='notification_object_id')
    message__icontains = django_filters.CharFilter(field_name='notification_object__message',
                                                   lookup_expr='icontains')
    action = django_filters.CharFilter(field_name='notification_object__action')
    timestamp__lt = django_filters.DateTimeFilter(field_name='notification_object__timestamp',
                                                  lookup_expr='lt')
    timestamp__gt = django_filters.DateTimeFilter(field_name='notification_object__timestamp',
                                                  lookup_expr='gt')

    channel_name = django_filters.CharFilter(field_name='notification_object__channel__content_type__model',
                                             lookup_expr='iexact')

    class Meta:
        model = Notification
        fields = dict(id=['exact'],
                      read=['exact'])


def notification_list(*, user: User, filters=None):
    filters = filters or {}
    qs = Notification.objects.filter(user=user,
                                     notification_object__timestamp__lte=timezone.now())

    return BaseNotificationFilter(filters, qs).qs


class BaseNotificationSubscriptionFilter(django_filters.FilterSet):
    channel_id = django_filters.CharFilter(field_name='channel_id')
    channel_name = django_filters.CharFilter(field_name='channel__content_type__model', lookup_expr='iexact')


def notification_subscription_list(*, user: User, filters=None):
    filters = filters or {}
    qs = NotificationSubscription.objects.filter(user=user).all()
    return BaseNotificationSubscriptionFilter(filters, qs).qs
