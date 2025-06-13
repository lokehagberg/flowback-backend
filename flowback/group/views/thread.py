from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.comment.views import CommentListAPI, CommentCreateAPI, CommentUpdateAPI, CommentDeleteAPI, CommentVoteAPI, \
    CommentAncestorListAPI
from flowback.files.serializers import FileSerializer
from flowback.group.selectors.thread import group_thread_list, group_thread_comment_list, \
    group_thread_comment_ancestor_list
from flowback.group.serializers import WorkGroupSerializer, GroupUserSerializer
from flowback.group.services.thread import (group_thread_create,
                                            group_thread_update,
                                            group_thread_delete,
                                            group_thread_comment_create,
                                            group_thread_comment_update,
                                            group_thread_comment_delete,
                                            group_thread_comment_vote,
                                            group_thread_vote_update)


@extend_schema(tags=['group/thread'])
class GroupThreadListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 1000

    class FilterSerializer(serializers.Serializer):
        order_by = serializers.CharField(required=False)
        id = serializers.IntegerField(required=False)
        id_list = serializers.CharField(required=False)
        title = serializers.CharField(required=False)
        title__icontains = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        group_ids = serializers.CharField(required=False)
        user_vote = serializers.BooleanField(required=False, allow_null=True, default=None)
        work_group_ids = serializers.CharField(required=False)

    class OutputSerializer(serializers.Serializer):
        created_by = GroupUserSerializer()
        created_at = serializers.DateTimeField()
        id = serializers.IntegerField()
        title = serializers.CharField()
        description = serializers.CharField(allow_null=True, default=None)
        pinned = serializers.BooleanField()
        total_comments = serializers.IntegerField()
        attachments = FileSerializer(many=True, source='attachments.filesegment_set', allow_null=True)
        score = serializers.IntegerField(default=0)
        user_vote = serializers.BooleanField(allow_null=True)
        work_group = WorkGroupSerializer()

    def get(self, request):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        threads = group_thread_list(fetched_by=request.user, filters=serializer.validated_data)
        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=threads,
                                      request=request,
                                      view=self)


@extend_schema(tags=['group/thread'])
class GroupThreadCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        title = serializers.CharField()
        description = serializers.CharField(required=False)
        pinned = serializers.BooleanField(default=False)
        attachments = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)
        work_group_id = serializers.IntegerField(required=False)

    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        thread = group_thread_create(user_id=request.user.id, group_id=group_id, **serializer.validated_data)
        return Response(status=status.HTTP_201_CREATED, data=thread.id)


@extend_schema(tags=['group/thread'])
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


@extend_schema(tags=['group/thread'])
class GroupThreadDeleteAPI(APIView):
    def post(self, request, thread_id: int):
        group_thread_delete(user_id=request.user, thread_id=thread_id)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/thread'])
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


@extend_schema(tags=['group/thread'])
class GroupThreadCommentListAPI(CommentListAPI):
    lazy_action = group_thread_comment_list


@extend_schema(tags=['group/thread'])
class GroupThreadCommentAncestorListAPI(CommentAncestorListAPI):
    lazy_action = group_thread_comment_ancestor_list


@extend_schema(tags=['group/thread'])
class GroupThreadCommentCreateAPI(CommentCreateAPI):
    lazy_action = group_thread_comment_create


@extend_schema(tags=['group/thread'])
class GroupThreadCommentUpdateAPI(CommentUpdateAPI):
    lazy_action = group_thread_comment_update


@extend_schema(tags=['group/thread'])
class GroupThreadCommentDeleteAPI(CommentDeleteAPI):
    lazy_action = group_thread_comment_delete


@extend_schema(tags=['group/thread'])
class GroupThreadCommentVoteAPI(CommentVoteAPI):
    lazy_action = group_thread_comment_vote
