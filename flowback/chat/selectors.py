from django.db.models import Q, OuterRef, Subquery, Case, When, F
import django_filters

from .models import MessageChannel, Message, MessageChannelParticipant, MessageChannelTopic
from flowback.user.models import User
from ..common.filters import NumberInFilter
from ..common.services import get_object


class BaseMessageFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc')))
    topic_name = django_filters.CharFilter(lookup_expr='exact', field_name='topic__name')
    user_ids = NumberInFilter()
    has_attachments = django_filters.BooleanFilter(method='has_attachments_filter')

    def has_attachments_filter(self, queryset, name, value):
        return queryset.filter(attachments__isnull=not value)

    class Meta:
        model = Message
        fields = dict(id=['exact'],
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

    timestamp = MessageChannelParticipant.objects.filter(user=user, channel=OuterRef('channel_id')).values('timestamp')
    qs = Message.objects.filter(Q(Q(channel__messagechannelparticipant__closed_at__isnull=True)
                                | Q(channel__messagechannelparticipant__closed_at__gt=F('created_at'))),
                                Q(Q(topic__isnull=True)
                                | Q(topic__hidden=False)),
                                channel__messagechannelparticipant__user=user,
                                active=True).annotate(timestamp=Subquery(timestamp)
                                                      ).distinct('channel').all()

    return BaseMessageChannelPreviewFilter(filters, qs).qs
