from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.views import APIView

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.group.models import GroupPermissions
from flowback.group.selectors import group_permissions_list
from flowback.group.services.permission import (group_permission_create,
                                                group_permission_update,
                                                group_permission_delete)


@extend_schema(tags=['group/permission'])
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
            fields = ('id',
                      'role_name',
                      'invite_user',
                      'create_poll',
                      'poll_fast_forward',
                      'poll_quorum',
                      'allow_vote',
                      'allow_delegate',
                      'send_group_email',
                      'kick_members',
                      'ban_members',

                      'create_proposal',
                      'update_proposal',
                      'delete_proposal',

                      'prediction_statement_create',
                      'prediction_statement_delete',

                      'prediction_bet_create',
                      'prediction_bet_update',
                      'prediction_bet_delete',

                      'create_kanban_task',
                      'update_kanban_task',
                      'delete_kanban_task',

                      'force_delete_poll',
                      'force_delete_proposal',
                      'force_delete_comment')

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


@extend_schema(tags=['group/permission'])
class GroupPermissionCreateApi(APIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = GroupPermissions
            fields = ('role_name',
                      'invite_user',
                      'create_poll',
                      'poll_fast_forward',
                      'poll_quorum',
                      'allow_vote',
                      'allow_delegate',
                      'kick_members',
                      'ban_members',

                      'create_proposal',
                      'update_proposal',
                      'delete_proposal',

                      'prediction_statement_create',
                      'prediction_statement_delete',

                      'prediction_bet_create',
                      'prediction_bet_update',
                      'prediction_bet_delete',

                      'create_kanban_task',
                      'update_kanban_task',
                      'delete_kanban_task',

                      'force_delete_poll',
                      'force_delete_proposal',
                      'force_delete_comment')

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_permission_create(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/permission'])
class GroupPermissionUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        permission_id = serializers.IntegerField()
        role_name = serializers.CharField(required=False)
        invite_user = serializers.BooleanField(required=False)
        create_poll = serializers.BooleanField(required=False)
        poll_fast_forward = serializers.BooleanField(required=False)
        poll_quorum = serializers.BooleanField(required=False)
        allow_vote = serializers.BooleanField(required=False)
        allow_delegate = serializers.BooleanField(required=False)
        kick_members = serializers.BooleanField(required=False)
        ban_members = serializers.BooleanField(required=False)
        send_group_email = serializers.BooleanField(required=False)

        create_proposal = serializers.BooleanField(required=False)
        update_proposal = serializers.BooleanField(required=False)
        delete_proposal = serializers.BooleanField(required=False)

        prediction_statement_create = serializers.BooleanField(required=False)
        prediction_statement_delete = serializers.BooleanField(required=False)

        prediction_bet_create = serializers.BooleanField(required=False)
        prediction_bet_update = serializers.BooleanField(required=False)
        prediction_bet_delete = serializers.BooleanField(required=False)

        create_kanban_task = serializers.BooleanField(required=False)
        update_kanban_task = serializers.BooleanField(required=False)
        delete_kanban_task = serializers.BooleanField(required=False)

        force_delete_poll = serializers.BooleanField(required=False)
        force_delete_proposal = serializers.BooleanField(required=False)
        force_delete_comment = serializers.BooleanField(required=False)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        permission_id = serializer.validated_data.pop('permission_id')
        group_permission_update(user=request.user.id,
                                group=group,
                                permission_id=permission_id,
                                data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/permission'])
class GroupPermissionDeleteApi(APIView):
    class InputSerializer(serializers.Serializer):
        permission_id = serializers.IntegerField()

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_permission_delete(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)
