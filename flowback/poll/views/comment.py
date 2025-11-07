from drf_spectacular.utils import extend_schema

from ..selectors.comment import poll_comment_list, poll_comment_ancestor_list

from ..services.comment import (poll_comment_create,
                                poll_comment_update,
                                poll_comment_delete,
                                poll_comment_vote)

from flowback.comment.views import (CommentListAPI,
                                    CommentCreateAPI,
                                    CommentUpdateAPI,
                                    CommentDeleteAPI,
                                    CommentVoteAPI,
                                    CommentAncestorListAPI)


@extend_schema(tags=['poll/comment'])
class PollCommentListAPI(CommentListAPI):
    lazy_action = poll_comment_list


@extend_schema(tags=['poll/comment'])
class PollCommentAncestorListAPI(CommentAncestorListAPI):
    lazy_action = poll_comment_ancestor_list


@extend_schema(tags=['poll/comment'])
class PollCommentCreateAPI(CommentCreateAPI):
    lazy_action = poll_comment_create


@extend_schema(tags=['poll/comment'])
class PollCommentUpdateAPI(CommentUpdateAPI):
    lazy_action = poll_comment_update


@extend_schema(tags=['poll/comment'])
class PollCommentDeleteAPI(CommentDeleteAPI):
    lazy_action = poll_comment_delete


@extend_schema(tags=['poll/comment'])
class PollCommentVoteAPI(CommentVoteAPI):
    lazy_action = poll_comment_vote
