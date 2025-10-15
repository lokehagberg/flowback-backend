from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.common.fields import CharacterSeparatedField
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.notification.selectors import notification_list, notification_subscription_list
from flowback.notification.models import NotificationChannel
from flowback.notification.services import notification_update


class NotificationListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 100
        default_limit = 20

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        read = serializers.BooleanField(required=False, allow_null=True, default=None)
        object_id = serializers.IntegerField(required=False)
        message__icontains = serializers.CharField(required=False)
        action = serializers.CharField(required=False)
        timestamp__lt = serializers.DateTimeField(required=False)
        timestamp__gt = serializers.DateTimeField(required=False)
        exclude_reminders = serializers.BooleanField(default=False, required=False)

        channel_name = serializers.CharField(required=False)
        order_by = serializers.ChoiceField(required=False, choices=['timestamp_asc',
                                                                    'timestamp_desc'])

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        read = serializers.BooleanField()

        object_id = serializers.IntegerField(source='notification_object_id')
        message = serializers.CharField(source='notification_object.message')
        data = serializers.JSONField(source='notification_object.data')
        timestamp = serializers.DateTimeField(source='notification_object.timestamp')
        action = serializers.CharField(source='notification_object.action')
        tag = serializers.CharField(source='notification_object.tag')
        reminder = serializers.IntegerField()

        channel_name = serializers.CharField(source='notification_object.channel.content_type.model')
        channel_data = serializers.JSONField(source='notification_object.channel.data')

    def get(self, request):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        notifications = notification_list(user=request.user, filters=filter_serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=notifications,
                                      request=request,
                                      view=self)


class NotificationSubscriptionListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 25
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        channel_id = serializers.IntegerField(required=False)
        channel_name = serializers.CharField(required=False)

    class OutputSerializer(serializers.Serializer):
        class NotificationSubscriptionTagSerializer(serializers.Serializer):
            tag = serializers.CharField()
            reminders = serializers.ListField(child=serializers.IntegerField(), allow_null=True)

        channel_id = serializers.IntegerField()
        channel_name = serializers.CharField(source='channel.name')
        tags = NotificationSubscriptionTagSerializer(many=True, source='notificationsubscriptiontag_set')

    def get(self, request):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        subscriptions = notification_subscription_list(user=request.user, filters=filter_serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=subscriptions,
                                      request=request,
                                      view=self)


class NotificationSubscribeTemplateAPI(APIView):
    """
    A Notification Subscription API constructor. Inherit this to a parent class,
    replace lazy_action field with a service of your own. Override and inherit the internal FilterSerializer,
    add any additional fields to it to pass onto the lazy_action.
    """
    lazy_action = NotificationChannel.subscribe
    notification_channel: NotificationChannel = None
    description = "Subscribe to a notification channel."

    class Pagination(LimitOffsetPagination):
        default_limit = 25

    class FilterSerializer(serializers.Serializer):
        tags = CharacterSeparatedField(child=serializers.CharField(), required=False, allow_null=True, default=None)
        reminders = CharacterSeparatedField(child=serializers.IntegerField(),
                                            required=False,
                                            allow_null=True,
                                            default=None)

    def post(self, request, *args, **kwargs):
        serializer = self.FilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.lazy_action.__func__(*args,
                                  user=request.user,
                                  **kwargs,
                                  **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class NotificationUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        notification_object_ids = CharacterSeparatedField(child=serializers.IntegerField(),
                                                          help_text='List of notification object IDs to mark as read, '
                                                                    'separated by commas.')
        read = serializers.BooleanField()

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification_update(user=request.user, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)
