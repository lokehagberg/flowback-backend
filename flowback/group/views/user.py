from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response

from flowback.group.models import GroupUser
from flowback.group.selectors import group_user_list


from flowback.group.services import group_join, group_user_update, group_leave, group_invite, group_invite_accept, \
    group_invite_reject


class GroupUserListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 1

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        user_id = serializers.IntegerField(required=False)
        username__icontains = serializers.CharField(required=False)
        delegate = serializers.BooleanField(required=False)
        is_admin = serializers.BooleanField(required=False)
        permission = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        username = serializers.CharField(source='user__username')
        profile_image = serializers.ImageField(source='user__profile_image')
        banner_image = serializers.ImageField(source='user__banner_image')
        delegate = serializers.PrimaryKeyRelatedField(source='groupuserdelegate', read_only=True)
        permission_id = serializers.IntegerField(source='permission')
        permission_name = serializers.CharField(source='permission__role_name')

        class Meta:
            model = GroupUser
            fields = ('id', 'user_id', 'group', 'is_admin', 'permission')

    def get(self, request, group: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        users = group_user_list(group=group,
                                fetched_by=request.user,
                                filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=users,
            request=request,
            view=self
        )


class GroupJoinApi(APIView):
    def post(self, request, group: int):
        data = group_join(user=request.user.id, group=group)

        if isinstance(data, GroupUser):
            return Response(status=status.HTTP_200_OK, data='join')

        else:
            return Response(status=status.HTTP_200_OK, data='invite')


class GroupLeaveApi(APIView):
    def post(self, request, group: int):
        group_leave(user=request.user.id, group=group)

        return Response(status=status.HTTP_200_OK)


class GroupUserUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        user = serializers.IntegerField(required=False)
        delegate = serializers.BooleanField(required=False)
        permission = serializers.IntegerField(required=False, allow_null=True)
        is_admin = serializers.IntegerField(required=False)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_to_update = request.user.id
        if serializer.validated_data.get('user'):
            user_to_update = serializer.validated_data.pop('user')

        group_user_update(user=user_to_update,
                          group=group,
                          fetched_by=request.user.id,
                          data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class GroupInviteApi(APIView):
    class InputSerializer(serializers.Serializer):
        to = serializers.IntegerField()

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_invite(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class GroupInviteAcceptApi(APIView):
    def post(self, request, group: int):
        group_invite_accept(user=request.user.id, group=group)


class GroupInviteRejectApi(APIView):
    def post(self, request, group: int):
        group_invite_reject(user=request.user.id, group=group)
