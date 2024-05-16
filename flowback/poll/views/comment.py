from drf_spectacular.utils import extend_schema

from ..selectors.comment import poll_comment_list
from ..services.comment import (poll_comment_create,
                                poll_comment_update,
                                poll_comment_delete)

from flowback.comment.views import CommentListAPI, CommentCreateAPI, CommentUpdateAPI, CommentDeleteAPI


@extend_schema(tags=['poll'])
class PollCommentListAPI(CommentListAPI):
    lazy_action = poll_comment_list


@extend_schema(tags=['poll'])
class PollCommentCreateAPI(CommentCreateAPI):
    lazy_action = poll_comment_create


@extend_schema(tags=['poll'])
class PollCommentUpdateAPI(CommentUpdateAPI):
    lazy_action = poll_comment_update


@extend_schema(tags=['poll'])
class PollCommentDeleteAPI(CommentDeleteAPI):
    lazy_action = poll_comment_delete
