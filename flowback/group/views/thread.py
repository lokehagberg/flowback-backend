from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.comment.views import CommentListAPI, CommentCreateAPI, CommentUpdateAPI, CommentDeleteAPI, CommentVoteAPI, \
    CommentAncestorListAPI
from flowback.files.serializers import FileSerializer
from flowback.group.selectors import group_thread_list, group_thread_comment_list, group_thread_comment_ancestor_list
from flowback.group.services.thread import (group_thread_create,
                                            group_thread_update,
                                            group_thread_delete,
                                            group_thread_comment_create,
                                            group_thread_comment_update,
                                            group_thread_comment_delete,
                                            group_thread_notification_subscribe,
                                            group_thread_notification,
                                            group_thread_comment_vote,
                                            group_thread_vote_update)
from flowback.user.serializers import BasicUserSerializer


class GroupThreadListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 1000

    class FilterSerializer(serializers.Serializer):
        order_by = serializers.CharField(required=False)
        id = serializers.IntegerField(required=False)
        id_list = serializers.CharField(required=False)
        title = serializers.CharField(required=False)
        user_vote = serializers.BooleanField(required=False, allow_null=True, default=None)

    class OutputSerializer(serializers.Serializer):
        created_by = BasicUserSerializer(source='created_by.user')
        id = serializers.IntegerField()
        title = serializers.CharField()
        description = serializers.CharField(allow_null=True, default=None)
        pinned = serializers.BooleanField()
        total_comments = serializers.IntegerField()
        attachments = FileSerializer(many=True, source='attachments.filesegment_set', allow_null=True)
        score = serializers.IntegerField(default=0)
        user_vote = serializers.BooleanField(allow_null=True)

    def get(self, request, group_id: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        threads = group_thread_list(group_id=group_id, fetched_by=request.user, filters=serializer.validated_data)
        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=threads,
                                      request=request,
                                      view=self)


class GroupThreadCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        title = serializers.CharField()
        description = serializers.CharField(required=False)
        pinned = serializers.BooleanField(default=False)
        attachments = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)

    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        thread = group_thread_create(user_id=request.user.id, group_id=group_id, **serializer.validated_data)
        return Response(status=status.HTTP_201_CREATED, data=thread.id)


class GroupThreadUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        title = serializers.CharField(required=False)
        pinned = serializers.BooleanField(allow_null=True, default=None)
        attachments = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)

    def post(self, request, thread_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_thread_update(user_id=request.user.id, thread_id=thread_id, data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class GroupThreadDeleteAPI(APIView):
    def post(self, request, thread_id: int):
        group_thread_delete(user_id=request.user, thread_id=thread_id)

        return Response(status=status.HTTP_200_OK)


class GroupThreadNotificationSubscribeAPI(APIView):
    class InputSerializer(serializers.Serializer):
        categories = serializers.MultipleChoiceField(choices=group_thread_notification.possible_categories)

    def post(self, request, thread_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group_thread_notification_subscribe(user_id=request.user.id, thread_id=thread_id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class GroupThreadVoteUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        vote = serializers.BooleanField(required=False, allow_null=True, default=None)

    def post(self, request, thread_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_thread_vote_update(user_id=request.user.id,
                                 thread_id=thread_id,
                                 **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class GroupThreadCommentListAPI(CommentListAPI):
    lazy_action = group_thread_comment_list


class GroupThreadCommentAncestorListAPI(CommentAncestorListAPI):
    lazy_action = group_thread_comment_ancestor_list


class GroupThreadCommentCreateAPI(CommentCreateAPI):
    lazy_action = group_thread_comment_create


class GroupThreadCommentUpdateAPI(CommentUpdateAPI):
    lazy_action = group_thread_comment_update


class GroupThreadCommentDeleteAPI(CommentDeleteAPI):
    lazy_action = group_thread_comment_delete


class GroupThreadCommentVoteAPI(CommentVoteAPI):
    lazy_action = group_thread_comment_vote
