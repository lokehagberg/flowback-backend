from django.db.models import Q, OuterRef, Subquery, Case, When
import django_filters

from .models import MessageChannel, Message, MessageChannelParticipant, MessageChannelTopic
from flowback.user.models import User
from ..common.services import get_object


class BaseMessageFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc')))
    topic_name = django_filters.CharFilter(lookup_expr='exact', field_name='topic__name')

    class Meta:
        model = Message
        fields = dict(id=['exact'],
                      user_id=['exact'],
                      message=['icontains'],
                      topic_id=['exact'],
                      parent_id=['exact'],
                      created_at=['gte', 'lte'])


def message_list(*, user: User, channel_id: int, **filters):
    filters = filters or {}
    participant = get_object(MessageChannelParticipant, channel_id=channel_id, user=user)

    qs = Message.objects.filter(channel=participant.channel).all()

    return BaseMessageFilter(filters, qs).qs


class BaseTopicFilter(django_filters.FilterSet):
    class Meta:
        model = MessageChannelTopic
        fields = dict(id=['exact'],
                      name=['exact', 'icontains'])


def message_channel_topic_list(*, user: User, channel_id: int, **filters):
    filters = filters or {}
    participant = get_object(MessageChannelParticipant, channel_id=channel_id, user=user)

    qs = MessageChannelTopic.objects.filter(channel=participant.channel).all()
    return BaseTopicFilter(filters, qs).qs


class BaseMessageChannelPreviewFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('timestamp', 'timestamp_asc'),
                                                     ('-timestamp', 'timestamp_desc')))

    username__icontains = django_filters.CharFilter(field_name='target__username', lookup_expr='icontains')
    origin_name = django_filters.CharFilter(field_name='channel__origin_name', lookup_expr='exact')
    topic_name = django_filters.CharFilter(field_name='topic__name', lookup_expr='exact')

    class Meta:
        model = Message
        fields = dict(id=['exact'],
                      user_id=['exact'],
                      created_at=['gte', 'lte'],
                      channel_id=['exact'],
                      topic_id=['exact'])


def message_channel_preview_list(*, user: User, **filters):
    filters = filters or {}

    timestamp = MessageChannelParticipant.objects.filter(user=user, channel=OuterRef('channel')).values('timestamp')
    active = MessageChannelParticipant.objects.filter(user=user, channel=OuterRef('channel')).annotate(
        active=Case(When(closed_at__isnull=True, then=True),
                    When(closed_at__gt=OuterRef('created_at'), then=False),
                    default=True)).values('active')
    qs = Message.objects.filter(channel__messagechannelparticipant__user=user).annotate(
        timestamp=Subquery(timestamp), active=Subquery(active)).filter(active=True).distinct('channel').all()

    return BaseMessageChannelPreviewFilter(filters, qs).qs

