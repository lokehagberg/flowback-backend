from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.views import APIView

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.group.models import GroupPermissions
from flowback.group.selectors import group_permissions_list
from flowback.group.services import group_permission_create, group_permission_update, group_permission_delete


class GroupPermissionListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 1

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        role_name = serializers.CharField(required=False)
        role_name__icontains = serializers.CharField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = GroupPermissions
            fields = ('role_name', 'invite_user', 'create_poll',
                      'allow_vote', 'kick_members', 'ban_members')

    def get(self, request, group: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        permissions = group_permissions_list(group=group,
                                             fetched_by=request.user,
                                             filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=permissions,
            request=request,
            view=self
        )


class GroupPermissionCreateApi(APIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = GroupPermissions
            fields = ('role_name', 'invite_user', 'create_poll',
                      'allow_vote', 'kick_members', 'ban_members')

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_permission_create(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class GroupPermissionUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        permission_id = serializers.IntegerField(source='permission')
        role_name = serializers.BooleanField(default=False)
        invite_user = serializers.BooleanField(default=False)
        create_poll = serializers.BooleanField(default=False)
        allow_vote = serializers.BooleanField(default=False)
        kick_members = serializers.BooleanField(default=False)
        ban_members = serializers.BooleanField(default=False)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        permission_id = serializer.validated_data.pop('permission_id')
        group_permission_update(user=request.user.id,
                                group=group,
                                permission_id=permission_id,
                                **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class GroupPermissionDeleteApi(APIView):
    class InputSerializer(serializers.Serializer):
        permission_id = serializers.IntegerField(source='permission')

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_permission_delete(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)
