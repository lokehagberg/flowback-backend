from rest_framework import serializers, status
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.group.models import Group, GroupFolder
from flowback.group.selectors import group_list, group_detail, group_folder_list
from flowback.group.services import group_delete, group_update, group_create, group_mail, group_notification, \
    group_notification_subscribe


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
                      'member_count')

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


class GroupFolderListApi(APIView): #use serializers.Serializers
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
                      'jitsi_room')

    def get(self, request, group: int):
        group = group_detail(fetched_by=request.user, group_id=group)

        serializer = self.OutputSerializer(group)
        return Response(serializer.data)


class GroupCreateApi(APIView):
    class InputSerializer(serializers.ModelSerializer):
        image = serializers.ImageField(required=False)
        cover_image = serializers.ImageField(required=False)

        class Meta:
            model = Group
            fields = ('name', 'description', 'hide_poll_users', 'direct_join', 'public', 'image', 'cover_image')

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group = group_create(user=request.user.id, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK, data=group.id)


class GroupUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        image = serializers.ImageField(required=False)
        cover_image = serializers.ImageField(required=False)
        public = serializers.BooleanField(required=False)
        hide_poll_users = serializers.BooleanField(required=False)
        direct_join = serializers.BooleanField(required=False)
        default_permission = serializers.IntegerField(required=False, allow_null=True)
        default_quorum = serializers.IntegerField(required=False, allow_null=True)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_update(user=request.user.id, group=group, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


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


class GroupMailApi(APIView):
    class InputSerializer(serializers.Serializer):
        title = serializers.CharField()
        message = serializers.CharField()

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_mail(fetched_by=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)
