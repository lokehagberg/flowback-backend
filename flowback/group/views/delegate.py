from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.common.filters import NumberInFilter
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response

from flowback.group.models import GroupUserDelegator, GroupTags
from flowback.group.selectors.user import group_user_delegate_list
from flowback.group.selectors.delegate import group_user_delegate_pool_list
from flowback.group.serializers import GroupUserSerializer
from flowback.group.services.delegate import group_user_delegate, group_user_delegate_update, \
    group_user_delegate_remove, \
    group_user_delegate_pool_create, group_user_delegate_pool_delete, group_user_delegate_pool_notification_subscribe
from flowback.notification.views import NotificationSubscribeTemplateAPI


@extend_schema(tags=['group/delegate'])
class GroupUserDelegatePoolListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        group_user_id = serializers.IntegerField(required=False)
        delegate_id = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.Serializer):
        class Delegates(serializers.Serializer):
            group_user = GroupUserSerializer()

        id = serializers.IntegerField()
        delegates = Delegates(many=True,
                              source='groupuserdelegate_set',
                              read_only=True)

    def get(self, request, group: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        pools = group_user_delegate_pool_list(group=group,
                                              fetched_by=request.user,
                                              filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=pools,
            request=request,
            view=self
        )


@extend_schema(tags=['group/delegate'])
class GroupUserDelegateListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        delegate_id = serializers.IntegerField(required=False)
        delegate_user_id = serializers.IntegerField(required=False)
        delegate_name__icontains = serializers.CharField(required=False)
        tag_id = serializers.IntegerField(required=False)
        tag_name = serializers.CharField(required=False)
        tag_name__icontains = serializers.CharField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class Delegates(serializers.Serializer):
            delegate_id = serializers.IntegerField(source='id')
            group_user_id = serializers.IntegerField()
            user_id = serializers.IntegerField(source='group_user.user_id')

        class Tags(serializers.ModelSerializer):
            class Meta:
                model = GroupTags
                fields = ('id', 'name')

        tags = Tags(many=True,
                    read_only=True)

        delegates = Delegates(many=True,
                              source='delegate_pool.groupuserdelegate_set',
                              read_only=True)
        blockchain_id = serializers.IntegerField(source='delegate_pool.blockchain_id')
        class Meta:
            model = GroupUserDelegator
            fields = ('id', 'tags', 'delegates', 'delegate_pool_id', 'blockchain_id')

    def get(self, request, group: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        tags = group_user_delegate_list(group=group,
                                        fetched_by=request.user,
                                        filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=tags,
            request=request,
            view=self
        )


@extend_schema(tags=['group/delegate'])
class GroupUserDelegatePoolCreateApi(APIView):
    class InputSerializer(serializers.Serializer):
        blockchain_id = serializers.IntegerField(required=False, min_value=1)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_user_delegate_pool_create(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/delegate'])
class GroupUserDelegatePoolDeleteApi(APIView):
    def post(self, request, group: int):
        group_user_delegate_pool_delete(user=request.user.id, group=group)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/delegate'])
class GroupUserDelegatePoolNotificationSubscribeAPI(NotificationSubscribeTemplateAPI):
    lazy_action = group_user_delegate_pool_notification_subscribe


@extend_schema(tags=['group/delegate'])
class GroupUserDelegateApi(APIView):
    class InputSerializer(serializers.Serializer):
        delegate_pool_id = serializers.IntegerField()
        tags = serializers.ListField(child=serializers.IntegerField(), required=False)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_user_delegate(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/delegate'])
class GroupUserDelegateUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        delegate_pool_id = serializers.IntegerField()
        tags = NumberInFilter()

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        group_user_delegate_update(user_id=request.user.id, group_id=group, data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/delegate'])
class GroupUserDelegateDeleteApi(APIView):
    class InputSerializer(serializers.Serializer):
        delegate_pool_id = serializers.IntegerField()

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_user_delegate_remove(user_id=request.user.id, group_id=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)
