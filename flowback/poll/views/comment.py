from drf_spectacular.utils import extend_schema

from rest_framework import status
from rest_framework.views import Response

from flowback.common.pagination import get_paginated_response

from ..selectors.comment import poll_comment_list
from ..services.comment import poll_comment_create, poll_comment_update, poll_comment_delete

from flowback.comment.views import CommentListAPI, CommentCreateAPI, CommentUpdateAPI, CommentDeleteAPI
from ...comment.models import Comment
from ...files.models import FileSegment
from ...user.models import User


@extend_schema(tags=['poll'])
class PollCommentListAPI(CommentListAPI):
    def get(self, request, poll: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        comments = poll_comment_list(fetched_by=request.user, poll_id=poll, filters=serializer.validated_data)

        print(FileSegment.objects.first().file)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=comments,
                                      request=request,
                                      view=self)


@extend_schema(tags=['poll'])
class PollCommentCreateAPI(CommentCreateAPI):
    def post(self, request, poll: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = poll_comment_create(author_id=request.user.id, poll_id=poll, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK, data=comment.id)


@extend_schema(tags=['poll'])
class PollCommentUpdateAPI(CommentUpdateAPI):
    def post(self, request, poll: int, comment_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        poll_comment_update(fetched_by=request.user.id,
                            poll_id=poll,
                            comment_id=comment_id,
                            data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll'])
class PollCommentDeleteAPI(CommentDeleteAPI):
    def post(self, request, poll: int, comment_id: int):
        poll_comment_delete(fetched_by=request.user.id, poll_id=poll, comment_id=comment_id)

        return Response(status=status.HTTP_200_OK)