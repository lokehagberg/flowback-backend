from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response

from flowback.group.models import GroupUser
from flowback.group.selectors.user import group_user_list, group_user_invite_list
from flowback.group.serializers import GroupUserSerializer

from flowback.group.services.group import group_user_update, group_join, group_leave, group_user_delete
from flowback.group.services.invite import group_invite, group_invite_accept, group_invite_reject


@extend_schema(tags=['group'])
class GroupUserListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 20
        max_limit = 1000

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        user_id = serializers.IntegerField(required=False)
        username__icontains = serializers.CharField(required=False)
        is_delegate = serializers.BooleanField(required=False, default=None, allow_null=True)
        is_admin = serializers.BooleanField(required=False, default=None, allow_null=True)
        permission = serializers.IntegerField(required=False)

    class OutputSerializer(GroupUserSerializer):
        delegate_pool_id = serializers.IntegerField(allow_null=True)
        work_groups = serializers.ListField(allow_null=True, child=serializers.CharField())

    def get(self, request, group_id: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        users = group_user_list(group_id=group_id,
                                fetched_by=request.user,
                                filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=users,
            request=request,
            view=self
        )


@extend_schema(tags=['group'])
class GroupInviteListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 20

    class FilterSerializer(serializers.Serializer):
        user = serializers.IntegerField(required=False)
        username__icontains = serializers.CharField(required=False)
        group = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.Serializer):
        user = serializers.IntegerField(source='user_id')
        username = serializers.CharField(source='user.username')
        profile_image = serializers.ImageField(source='user.profile_image')
        group = serializers.IntegerField(source='group_id')
        group_name = serializers.CharField(source='group.name')
        group_image = serializers.ImageField(source='group.image')
        external = serializers.BooleanField()

    def get(self, request, group: int = None):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        invites = group_user_invite_list(group=group,
                                         fetched_by=request.user,
                                         filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=invites,
            request=request,
            view=self
        )


@extend_schema(tags=['group'])
class GroupJoinApi(APIView):
    def post(self, request, group: int):
        data = group_join(user=request.user.id, group=group)

        if isinstance(data, GroupUser):
            return Response(status=status.HTTP_200_OK, data='join')

        else:
            return Response(status=status.HTTP_200_OK, data='invite')


@extend_schema(tags=['group'])
class GroupLeaveApi(APIView):
    def post(self, request, group: int):
        group_leave(user=request.user.id, group=group)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group'])
class GroupUserUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        target_user_id = serializers.IntegerField()
        permission = serializers.IntegerField(required=False, allow_null=True, source='permission_id')
        is_admin = serializers.BooleanField(required=False, allow_null=True, default=None)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user_id = request.user.id
        if serializer.validated_data.get('target_user_id'):
            target_user_id = serializer.validated_data.pop('target_user_id')

        group_user_update(fetched_by=request.user,
                          target_user_id=target_user_id,
                          group=group,
                          data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group'])
class GroupInviteApi(APIView):
    class InputSerializer(serializers.Serializer):
        to = serializers.IntegerField()

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_invite(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group'])
class GroupInviteAcceptApi(APIView):
    class InputSerializer(serializers.Serializer):
        to = serializers.IntegerField(required=False)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        group_invite_accept(fetched_by=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group'])
class GroupInviteRejectApi(APIView):
    class InputSerializer(serializers.Serializer):
        to = serializers.IntegerField(required=False)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        group_invite_reject(fetched_by=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group'])
class GroupUserDeleteAPI(APIView):
    class InputSerializer(serializers.Serializer):
        target_user_id = serializers.IntegerField()

    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_user_delete(user_id=request.user.id, group_id=group_id, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)
