from drf_spectacular.utils import extend_schema

from flowback.comment.views import CommentListAPI, CommentCreateAPI, CommentUpdateAPI, CommentDeleteAPI, CommentVoteAPI
from flowback.group.selectors import group_delegate_pool_comment_list
from flowback.group.services.delegate import (group_delegate_pool_comment_create,
                                              group_delegate_pool_comment_update,
                                              group_delegate_pool_comment_delete,
                                              group_delegate_pool_comment_vote)


@extend_schema(tags=['group/delegate'])
class GroupDelegatePoolCommentListAPI(CommentListAPI):
    lazy_action = group_delegate_pool_comment_list


@extend_schema(tags=['group/delegate'])
class GroupDelegatePoolCommentCreateAPI(CommentCreateAPI):
    lazy_action = group_delegate_pool_comment_create


@extend_schema(tags=['group/delegate'])
class GroupDelegatePoolCommentUpdateAPI(CommentUpdateAPI):
    lazy_action = group_delegate_pool_comment_update


@extend_schema(tags=['group/delegate'])
class GroupDelegatePoolCommentDeleteAPI(CommentDeleteAPI):
    lazy_action = group_delegate_pool_comment_delete


@extend_schema(tags=['group/delegate'])
class GroupDelegatePoolCommentVoteAPI(CommentVoteAPI):
    lazy_action = group_delegate_pool_comment_vote
