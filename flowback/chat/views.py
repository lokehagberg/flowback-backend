from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .selectors import message_list, message_channel_preview_list, message_channel_topic_list
from .serializers import MessageSerializer, BasicMessageSerializer
from .services import message_channel_userdata_update, message_channel_leave, message_files_upload, get_ancestor, get_descendants
from flowback.common.pagination import get_paginated_response, LimitOffsetPagination


class MessageListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 50

    class FilterSerializer(serializers.Serializer):
        order_by = serializers.ChoiceField(required=False, choices=['created_at_asc', 'created_at_desc',
                                                                    'total_replies_asc', 'total_replies_desc'])
        id = serializers.IntegerField(required=False)
        user_ids = serializers.CharField(required=False)
        message__icontains = serializers.CharField(required=False)
        parent_id = serializers.IntegerField(required=False)
        topic_id = serializers.IntegerField(required=False)
        topic_name = serializers.CharField(required=False)
        has_attachments = serializers.BooleanField(required=False, allow_null=True, default=None)
        created_at__gte = serializers.DateTimeField(required=False)
        created_at__lte = serializers.DateTimeField(required=False)

    OutputSerializer = MessageSerializer

    def get(self, request, channel_id: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        messages = message_list(user=request.user, channel_id=channel_id, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=messages,
                                      request=request,
                                      view=self)


class MessageChannelPreviewAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 50

    class FilterSerializer(serializers.Serializer):
        order_by = serializers.ChoiceField(required=False, choices=['timestamp_asc', 'timestamp_desc'])
        origin_name = serializers.CharField(required=False)
        username__icontains = serializers.CharField(required=False)
        id = serializers.IntegerField(required=False)
        user_id = serializers.IntegerField(required=False)
        created_at__gte = serializers.DateTimeField(required=False)
        created_at__lte = serializers.DateTimeField(required=False)
        channel_id = serializers.IntegerField(required=False)
        topic_id = serializers.IntegerField(required=False)
        topic_name = serializers.CharField(required=False)

    class OutputSerializer(BasicMessageSerializer):
        timestamp = serializers.DateTimeField(allow_null=True)

    def get(self, request):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        messages = message_channel_preview_list(user=request.user, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=messages,
                                      request=request,
                                      view=self)


class MessageChannelTopicListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        topic_id = serializers.IntegerField()
        name = serializers.CharField()
        name__icontains = serializers.CharField()

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        name = serializers.CharField()

    def get(self, request, channel_id: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        topics = message_channel_topic_list(user=request.user, channel_id=channel_id, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=topics,
                                      request=request,
                                      view=self)


class MessageFileCollectionUploadAPI(APIView):
    class InputSerializer(serializers.Serializer):
        files = serializers.ListField(child=serializers.FileField())

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()

    def post(self, request, channel_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_collection = message_files_upload(user_id=request.user.id, channel_id=channel_id,
                                               **serializer.validated_data)
        return Response(status=status.HTTP_201_CREATED, data=self.OutputSerializer(file_collection).data)


class MessageChannelUserDataUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        channel_id = serializers.IntegerField()
        timestamp = serializers.DateTimeField(required=False)
        closed_at = serializers.DateTimeField(required=False)

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message_channel_userdata_update(user_id=request.user.id, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class MessageChannelLeaveAPI(APIView):
    class InputSerializer(serializers.Serializer):
        channel_id = serializers.IntegerField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message_channel_leave(user_id=request.user.id, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)

class GetAllParentsOfCommentAPI(APIView):
    ''' This api will return all parent comments of given comment id'''
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 100
    class InputSerializer(serializers.Serializer):
        channel_id = serializers.IntegerField()
        comment_id = serializers.IntegerField()
        limit = serializers.IntegerField(required=False)

    OutputSerializer = MessageSerializer

    def get(self, request):
        serializer = self.InputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        ancestor = get_ancestor(**serializer.validated_data, self_include=True).order_by('id')

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=ancestor,
                                      request=request,
                                      view=self)
        
class GetAllChildsOfCommentAPI(APIView):
    '''This api will return all childs of given comment id'''
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 100
    class InputSerializer(serializers.Serializer):
        channel_id = serializers.IntegerField()
        comment_id = serializers.IntegerField()
        limit = serializers.IntegerField(required=False)

    OutputSerializer = MessageSerializer

    def get(self, request):
        serializer = self.InputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        descendants = get_descendants(**serializer.validated_data, self_include=True).order_by('id')

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=descendants,
                                      request=request,
                                      view=self)     
        