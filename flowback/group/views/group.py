from rest_framework import serializers, status
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.group.models import Group, GroupPermissions
from flowback.group.selectors import group_list, group_detail
from flowback.group.services import group_delete, group_update, group_permission_create, group_create, \
    group_permission_update


class GroupListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 1

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        name = serializers.CharField(required=False)
        name__icontains = serializers.CharField(required=False)
        direct_join = serializers.BooleanField(required=False)
        joined = serializers.BooleanField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Group
            fields = ('id',
                      'created_by',
                      'active',
                      'direct_join',
                      'name',
                      'description',
                      'image',
                      'cover_image',
                      'joined')

    def get(self, request):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        groups = group_list(fetched_by=request.user, filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=groups,
            request=request,
            view=self
        )


class GroupDetailSerializer(APIView):
    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Group
            fields = ('created_by',
                      'active',
                      'direct_join',
                      'public',
                      'default_permission'
                      'name',
                      'description',
                      'image',
                      'cover_image',
                      'jitsi_room')

    def get(self, request, group: int):
        group = group_detail(fetched_by=request.user, group_id=group)

        serializer = self.OutputSerializer(group)
        return Response(serializer.data)


class GroupCreateAPI(APIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Group
            fields = ('name', 'description', 'image', 'cover_image', 'direct_join', 'public')

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_create(user=request.user.id, **serializer.validated_data)


class GroupUpdateApi(APIView):
    class InputSerializer(serializers.ModelSerializer):

        class Meta:
            model = Group
            fields = ('name', 'description', 'image', 'cover_image', 'public',
                      'direct_join', 'default_permission')

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = group_update(user=request.user.id, group=group, data=serializer.validated_data)


class GroupDeleteApi(APIView):
    def post(self, request, group: int):
        group_delete(user=request.user.id, group=group)
        return Response(status=status.HTTP_200_OK)


class GroupPermissionCreateApi(APIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = GroupPermissions
            fields = ('role_name', 'invite_user', 'create_poll',
                      'allow_vote', 'kick_members', 'ban_members')

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_permission_create(user=request.user, group=group, **serializer.validated_data)


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
        group_permission_update(user=request.user,
                                group=group,
                                permission_id=permission_id,
                                **serializer.validated_data)
