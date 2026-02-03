from django.db.models import Q, OuterRef, Subquery, Case, When, F, Count
import django_filters
from rest_framework.exceptions import PermissionDenied

from .models import MessageChannel, Message, MessageChannelParticipant, MessageChannelTopic
from flowback.user.models import User
from ..common.filters import NumberInFilter, ExistsFilter, StringInFilter
from ..common.services import get_object


class BaseMessageFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc')))
    topic_name = django_filters.CharFilter(lookup_expr='exact', field_name='topic__name')
    user_ids = NumberInFilter()
    has_attachments = ExistsFilter(field_name='attachments')

    class Meta:
        model = Message
        fields = dict(id=['exact'],
                      message=['icontains'],
                      topic_id=['exact'],
                      parent_id=['exact'],
                      created_at=['gte', 'lte'])


def message_list(*, user: User, channel_id: int, filters=None):
    filters = filters or {}
    participant = get_object(MessageChannelParticipant, active=True, channel_id=channel_id, user=user)

    qs = Message.objects.filter(channel=participant.channel, active=True).all()

    return BaseMessageFilter(filters, qs).qs


class BaseTopicFilter(django_filters.FilterSet):
    class Meta:
        model = MessageChannelTopic
        fields = dict(id=['exact'],
                      name=['exact', 'icontains'])


def message_channel_topic_list(*, user: User, channel_id: int, filters=None):
    filters = filters or {}
    participant = get_object(MessageChannelParticipant, active=True, channel_id=channel_id, user=user)

    qs = MessageChannelTopic.objects.filter(channel=participant.channel).all()
    return BaseTopicFilter(filters, qs).qs


class BaseMessageChannelPreviewFilter(django_filters.FilterSet):
    origin_names = StringInFilter(field_name='channel__origin_name')
    title = django_filters.CharFilter(field_name='channel__title', lookup_expr='icontains')
    exclude_closed = django_filters.BooleanFilter(method='filter_exclude_closed')

    def filter_exclude_closed(self, queryset, name, value):
        if value:
            return queryset.filter(Q(closed_at__isnull=True)
                                   | Q(message_created_at__gt=F('closed_at')))
        return queryset

    class Meta:
        model = MessageChannelParticipant
        fields = dict(id=['exact'],
                      user_id=['exact'],
                      closed_at=['gte', 'lte'],
                      channel_id=['exact'])


def message_channel_preview_list(*, user: User, filters=None):
    filters = filters or {}
    message_qs = Message.objects.filter(channel=OuterRef('channel'),
                                        type='message',
                                        active=True).order_by('-created_at')[:1].values('created_at')
    qs = MessageChannelParticipant.objects.filter(
        user=user,
        active=True
    ).annotate(
        message_created_at=Subquery(message_qs)
    ).order_by('-message_created_at')

    participants = BaseMessageChannelPreviewFilter(filters, qs).qs

    return participants


class MessageChannelParticipantFilter(django_filters.FilterSet):
    username__icontains = django_filters.CharFilter(lookup_expr='icontains', field_name='user__username')

    class Meta:
        model = MessageChannelParticipant
        fields = dict(id=['exact'],
                      user_id=['exact'],
                      active=['exact'])


def message_channel_participant_list(*, user: User, channel_id: int, filters=None):
    filters = filters or {}

    try:
        participant = MessageChannelParticipant.objects.get(user=user, channel_id=channel_id)

    except MessageChannelParticipant.DoesNotExist:
        raise PermissionDenied("User is not a participant of this channel")

    qs = MessageChannelParticipant.objects.filter(channel=participant.channel
                                                  ).all().order_by('active', '-user__username')

    return BaseMessageChannelPreviewFilter(filters, qs).qs
