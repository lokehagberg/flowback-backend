from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.chat.selectors import group_message_list, group_message_preview, direct_message_list, \
    direct_message_preview
from flowback.chat.models import GroupMessage, DirectMessage
from flowback.chat.services import direct_chat_timestamp, group_chat_timestamp
from flowback.common.pagination import get_paginated_response, LimitOffsetPagination


class GroupMessageListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        user = serializers.IntegerField(required=False)
        username__icontains = serializers.CharField(required=False)
        message = serializers.CharField(required=False)
        created_at__lt = serializers.DateTimeField(required=False)
        created_at__gt = serializers.DateTimeField(required=False)
        order_by = serializers.CharField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        user_id = serializers.IntegerField(source='group_user.user_id')
        username = serializers.CharField(source='group_user.user.username')
        profile_image = serializers.ImageField(source='group_user.user.profile_image')

        class Meta:
            model = GroupMessage
            fields = 'username', 'user_id', 'profile_image', 'message', 'created_at'

    def get(self, request, group: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        messages = group_message_list(user=request.user.id,
                                      group=group,
                                      filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=messages,
            request=request,
            view=self
        )


class GroupMessagePreviewApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 1000

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        group = serializers.IntegerField(required=False)
        group_name__icontains = serializers.CharField(required=False)
        message__icontains = serializers.CharField(required=False)
        created_at__lt = serializers.DateTimeField(required=False)
        created_at__gt = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        group_id = serializers.IntegerField(source='group_user.group_id')
        user_id = serializers.IntegerField(source='group_user.user_id')
        username = serializers.CharField(source='group_user.user.username')
        profile_image = serializers.ImageField(source='group_user.user.profile_image')
        timestamp = serializers.DateTimeField()

        class Meta:
            model = GroupMessage
            fields = 'group_id', 'username', 'user_id', 'profile_image', 'message', 'created_at', 'timestamp'

    def get(self, request):
        messages = group_message_preview(user=request.user.id)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=messages,
            request=request,
            view=self
        )


class DirectMessageListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        target = serializers.IntegerField(required=False)
        order_by = serializers.CharField(required=False)
        created_at__lt = serializers.DateTimeField(required=False)
        created_at__gt = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        username = serializers.CharField(source='user.username')
        profile_image = serializers.ImageField(source='user.profile_image')

        class Meta:
            model = GroupMessage
            fields = 'username', 'profile_image', 'message', 'created_at'

    def get(self, request, target: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        messages = direct_message_list(user=request.user.id,
                                       target=target,
                                       filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=messages,
            request=request,
            view=self
        )


class DirectMessagePreviewApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 1000

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        target = serializers.IntegerField(required=False)
        message__icontains = serializers.CharField(required=False)
        created_at__lt = serializers.DateTimeField(required=False)
        created_at__gt = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        username = serializers.CharField(source='user.username')
        user_id = serializers.IntegerField(source='user.id')
        target_username = serializers.CharField(source='target.username')
        target_id = serializers.IntegerField(source='target.id')
        profile_image = serializers.ImageField(source='user.profile_image')
        timestamp = serializers.DateTimeField()

        class Meta:
            model = DirectMessage
            fields = ('username', 'user_id', 'target_username', 'target_id',
                      'profile_image', 'message', 'created_at', 'timestamp')

    def get(self, request):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        messages = direct_message_preview(user=request.user.id,
                                          filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=messages,
            request=request,
            view=self
        )


class DirectMessageTimestampApi(APIView):
    class InputSerializer(serializers.Serializer):
        timestamp = serializers.DateTimeField()

    def post(self, request, target: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        direct_chat_timestamp(user_id=request.user.id, target=target, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class GroupMessageTimestampApi(APIView):
    class InputSerializer(serializers.Serializer):
        timestamp = serializers.DateTimeField()

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_chat_timestamp(user_id=request.user.id, group_id=group, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)






