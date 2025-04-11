import django_filters
from django.utils import timezone

from .models import NotificationChannel, NotificationObject, Notification, NotificationSubscription
from ..user.models import User


class BaseNotificationFilter(django_filters.FilterSet):
    object_id = django_filters.NumberFilter(field_name='notification_object_id')
    message = django_filters.CharFilter(field_name='notification_object_message',
                                        lookup_expr='iexact')
    message__icontains = django_filters.CharFilter(field_name='notification_object_message',
                                                   lookup_expr='icontains')
    action = django_filters.CharFilter(field_name='notification_object__action')
    timestamp__lt = django_filters.DateFilter(field_name='notification_object__timestamp',
                                              lookup_expr='lt')
    timestamp__gt = django_filters.DateFilter(field_name='notification_object__timestamp',
                                              lookup_expr='gt')

    channel_sender_type = django_filters.CharFilter(field_name='notification_object__channel__sender_type')
    channel_sender_id = django_filters.NumberFilter(field_name='notification_object__channel__sender_id')

    channel_sender_category = django_filters.CharFilter(field_name='notification_object__channel__category')

    class Meta:
        model = Notification
        fields = dict(id=['exact'],
                      read=['exact'])


class BaseNotificationSubscriptionFilter(django_filters.FilterSet):
    channel_sender_type = django_filters.CharFilter(field_name='channel__sender_type')
    channel_sender_id = django_filters.NumberFilter(field_name='channel__sender_id')
    channel_category = django_filters.CharFilter(field_name='channel__category')
    order_by = django_filters.OrderingFilter(fields=('notification_object__timestamp_asc', 'notification_object__timestamp_desc'))


def notification_list(*, user: User, filters=None):
    filters = filters or {}
    qs = Notification.objects.filter(user=user,
                                     notification_object__timestamp__lte=timezone.now())
    
    order_by = filters.get('order_by')
    if order_by == 'notification_object__timestamp_asc':
        qs = qs.order_by('notification_object__timestamp')
    elif order_by == 'notification_object__timestamp_desc':
        qs = qs.order_by('-notification_object__timestamp')
    else:
        qs = qs.order_by('notification_object__timestamp')  # default ordering

    return BaseNotificationFilter(filters, qs).qs


def notification_subscription_list(*, user: User, filters=None):
    filters = filters or {}
    qs = NotificationSubscription.objects.filter(user=user).all()
    return BaseNotificationSubscriptionFilter(filters, qs).qs
