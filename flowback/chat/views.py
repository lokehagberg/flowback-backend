from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.chat.selectors import group_message_list, group_message_preview, direct_message_list, \
    direct_message_preview
from flowback.chat.models import GroupMessage
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

        class Meta:
            model = GroupMessage
            fields = 'group_id', 'username', 'user_id', 'profile_image', 'message', 'created_at'

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

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        target = serializers.IntegerField(required=False)
        message__icontains = serializers.CharField(required=False)
        created_at__lt = serializers.DateTimeField(required=False)
        created_at__gt = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        username = serializers.CharField(source='user.username')
        target_username = serializers.CharField(source='target.username')
        target_id = serializers.IntegerField(source='target.id')
        profile_image = serializers.ImageField(source='user.profile_image')

        class Meta:
            model = GroupMessage
            fields = 'username', 'user_id', 'target_username', 'target_id', 'profile_image', 'message', 'created_at'

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
