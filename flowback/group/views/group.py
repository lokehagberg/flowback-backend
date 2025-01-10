from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status, generics
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.group.models import Group
from flowback.group.selectors import group_list, group_detail, group_folder_list, work_group_user_list, \
    work_group_user_join_request_list, work_group_list
from flowback.group.serializers import GroupUserSerializer
from flowback.group.services.group import group_notification_subscribe
from flowback.group.services.group import group_notification, group_create, group_update, group_delete, group_mail
from flowback.group.services.workgroup import work_group_create, work_group_update, work_group_delete, \
    work_group_user_join, work_group_user_leave, work_group_user_add, work_group_user_remove, work_group_user_update


@extend_schema(tags=['group'])
class GroupListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 1

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        name = serializers.CharField(required=False)
        name__icontains = serializers.CharField(required=False)
        chat_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
        direct_join = serializers.BooleanField(required=False, default=None, allow_null=True)
        joined = serializers.BooleanField(required=False, default=None, allow_null=True)

    class OutputSerializer(serializers.ModelSerializer):
        joined = serializers.BooleanField()
        member_count = serializers.IntegerField()

        class Meta:
            model = Group
            fields = ('id',
                      'created_by',
                      'active',
                      'direct_join',
                      'hide_poll_users',
                      'name',
                      'description',
                      'image',
                      'cover_image',
                      'joined',
                      'chat_id',
                      'member_count',
                      'blockchain_id')

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


@extend_schema(tags=['group'])
class GroupFolderListApi(APIView):  #use serializers.Serializers
    class Pagination(LimitOffsetPagination):
        default_limit = 20
        max_limit = 100

    class OutputSerializer(serializers.Serializer):
        name = serializers.CharField()

    def get(self, request):
        group_folders = group_folder_list()

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=group_folders,
            request=request,
            view=self
        )


@extend_schema(tags=['group'])
class GroupDetailApi(APIView):
    class OutputSerializer(serializers.ModelSerializer):
        member_count = serializers.IntegerField()

        class Meta:
            model = Group
            fields = ('created_by',
                      'active',
                      'direct_join',
                      'public',
                      'hide_poll_users',
                      'default_permission',
                      'name',
                      'description',
                      'image',
                      'cover_image',
                      'member_count',
                      'chat_id',
                      'blockchain_id',
                      'jitsi_room')

    def get(self, request, group: int):
        group = group_detail(fetched_by=request.user, group_id=group)

        serializer = self.OutputSerializer(group)
        return Response(serializer.data)


@extend_schema(tags=['group'])
class GroupCreateApi(APIView):
    class InputSerializer(serializers.ModelSerializer):
        image = serializers.ImageField(required=False)
        cover_image = serializers.ImageField(required=False)

        class Meta:
            model = Group
            fields = ('name',
                      'description',
                      'hide_poll_users',
                      'direct_join',
                      'public',
                      'image',
                      'cover_image',
                      'blockchain_id')

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group = group_create(user=request.user.id, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK, data=group.id)


@extend_schema(tags=['group'])
class GroupUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        image = serializers.ImageField(required=False)
        cover_image = serializers.ImageField(required=False)
        public = serializers.BooleanField(required=False)
        hide_poll_users = serializers.BooleanField(required=False)
        poll_phase_minimum_space = serializers.IntegerField(required=False)
        direct_join = serializers.BooleanField(required=False)
        default_permission = serializers.IntegerField(required=False, allow_null=True)
        default_quorum = serializers.IntegerField(required=False, allow_null=True)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_update(user=request.user.id, group=group, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group'])
class GroupDeleteApi(APIView):
    def post(self, request, group: int):
        group_delete(user=request.user.id, group=group)
        return Response(status=status.HTTP_200_OK)


class GroupNotificationSubscribeApi(APIView):
    class InputSerializer(serializers.Serializer):
        categories = serializers.MultipleChoiceField(choices=group_notification.possible_categories)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_notification_subscribe(user_id=request.user.id, group=group, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group'])
class GroupMailApi(APIView):
    class InputSerializer(serializers.Serializer):
        title = serializers.CharField()
        message = serializers.CharField()
        work_group_id = serializers.IntegerField(required=False)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_mail(fetched_by=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/workgroup'])
class WorkGroupListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        pass

    class FilterSerializer(serializers.Serializer):
        joined = serializers.BooleanField(required=False, allow_null=True, default=None)
        id = serializers.IntegerField(required=False)
        name = serializers.CharField(required=False)
        name__icontains = serializers.CharField(required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        name = serializers.CharField()
        member_count = serializers.IntegerField()
        direct_join = serializers.BooleanField()

    def get(self, request, group_id: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        response = work_group_list(fetched_by=request.user, group_id=group_id, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=response,
                                      request=request,
                                      view=self)


@extend_schema(tags=['group/workgroup'])
class WorkGroupUserListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        user_id = serializers.IntegerField(required=False)
        group_user_id = serializers.IntegerField(required=False)
        username = serializers.CharField(required=False)
        order_by = serializers.ChoiceField(required=False, choices=['created_at_asc',
                                                                    'created_at_desc',
                                                                    'name_asc',
                                                                    'name_desc'])

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        work_group_id = serializers.IntegerField()
        work_group_name = serializers.CharField(source="work_group.name")
        group_user = GroupUserSerializer()
        is_moderator = serializers.BooleanField()

    def get(self, request, work_group_id: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        work_group_users = work_group_user_list(work_group_id=work_group_id,
                                                fetched_by=request.user,
                                                filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=work_group_users,
                                      request=request,
                                      view=self)

@extend_schema(tags=['group/workgroup'])
class WorkGroupUserJoinRequestListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        user_id = serializers.IntegerField(required=False)
        group_user_id = serializers.IntegerField(required=False)
        username = serializers.CharField(required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        work_group_id = serializers.IntegerField()
        work_group_name = serializers.CharField(source="work_group.name")
        group_user = GroupUserSerializer()

    def get(self, request, work_group_id: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        work_group_join_requests = work_group_user_join_request_list(work_group_id=work_group_id,
                                                                     fetched_by=request.user,
                                                                     filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=work_group_join_requests,
                                      request=request,
                                      view=self)


@extend_schema(tags=['group/workgroup'])
class WorkGroupCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField()
        direct_join = serializers.BooleanField(default=False)

    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        work_group = work_group_create(user_id=request.user.id, group_id=group_id, **serializer.validated_data)

        return Response(status=status.HTTP_201_CREATED, data=work_group.id)


@extend_schema(tags=['group/workgroup'])
class WorkGroupUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField()
        direct_join = serializers.BooleanField(required=False, allow_null=True, default=None)

    def post(self, request, work_group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        work_group_update(user_id=request.user.id, work_group_id=work_group_id, data=serializer.validated_data)

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['group/workgroup'])
class WorkGroupDeleteAPI(APIView):
    def post(self, request, work_group_id: int):
        work_group_delete(user_id=request.user.id, work_group_id=work_group_id)

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['group/workgroup'])
class WorkGroupUserJoinAPI(APIView):
    def post(self, request, work_group_id: int):
        work_group_user_join(user_id=request.user.id, work_group_id=work_group_id)

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['group/workgroup'])
class WorkGroupUserLeaveAPI(APIView):
    def post(self, request, work_group_id: int):
        work_group_user_leave(user_id=request.user.id, work_group_id=work_group_id)

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['group/workgroup'])
class WorkGroupUserAddAPI(APIView):
    class InputSerializer(serializers.Serializer):
        target_group_user_id = serializers.IntegerField()
        is_moderator = serializers.BooleanField(default=False)

    def post(self, request, work_group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        work_group_user = work_group_user_add(user_id=request.user.id,
                                              work_group_id=work_group_id,
                                              **serializer.validated_data)

        return Response(status=status.HTTP_200_OK, data=work_group_user.id)


@extend_schema(tags=['group/workgroup'])
class WorkGroupUserUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        target_group_user_id = serializers.IntegerField()
        is_moderator = serializers.BooleanField(required=False)

    def post(self, request, work_group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        work_group_user_update(user_id=request.user.id,
                               work_group_id=work_group_id,
                               target_group_user_id=serializer.validated_data.pop('target_group_user_id'),
                               data=serializer.validated_data)

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['group/workgroup'])
class WorkGroupUserRemoveAPI(APIView):
    class InputSerializer(serializers.Serializer):
        target_group_user_id = serializers.IntegerField()

    def post(self, request, work_group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        work_group_user_remove(user_id=request.user.id, work_group_id=work_group_id, **serializer.validated_data)

        return Response(status=status.HTTP_204_NO_CONTENT)
