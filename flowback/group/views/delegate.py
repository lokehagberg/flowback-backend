from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response

from flowback.group.models import GroupUserDelegator, GroupUserDelegatePool
from flowback.group.selectors import group_user_delegate_list, group_user_delegate_pool_list
from flowback.group.services import group_user_delegate, group_user_delegate_update, group_user_delegate_remove, \
    group_user_delegate_pool_create, group_user_delegate_pool_delete


class GroupUserDelegatePoolListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        group_user_id = serializers.IntegerField(required=False)
        delegate_id = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.Serializer):
        class Delegates(serializers.Serializer):
            delegate_id = serializers.IntegerField(source='id')
            user_id = serializers.IntegerField()

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

        groupdata = GroupUserDelegatePool.objects.first()
        print(groupdata.groupuserdelegate_set.all())

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=pools,
            request=request,
            view=self
        )


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

    class OutputSerializer(serializers.Serializer):
        class Meta:
            model = GroupUserDelegator
            fields = ('tags', 'delegate')

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


class GroupUserDelegatePoolCreateApi(APIView):
    def post(self, request, group: int):
        group_user_delegate_pool_create(user=request.user.id, group=group)

        return Response(status=status.HTTP_200_OK)


class GroupUserDelegatePoolDeleteApi(APIView):
    def post(self, request, group: int):
        group_user_delegate_pool_delete(user=request.user.id, group=group)

        return Response(status=status.HTTP_200_OK)


class GroupUserDelegateApi(APIView):
    class InputSerializer(serializers.Serializer):
        delegate = serializers.IntegerField()
        tags = serializers.ListField(child=serializers.IntegerField())

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_user_delegate(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class GroupUserDelegateUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        delegate_id = serializers.IntegerField(source='delegate')
        tags = serializers.ListField(child=serializers.IntegerField())

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_user_delegate_update(user_id=request.user.id, group_id=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class GroupUserDelegateDeleteApi(APIView):
    class InputSerializer(serializers.Serializer):
        delegate_id = serializers.IntegerField(source='id')

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_user_delegate_remove(user_id=request.user.id, group_id=group, **serializer.validated_data)
