from flowback.comment.views import CommentListAPI, CommentCreateAPI, CommentUpdateAPI, CommentDeleteAPI, CommentVoteAPI
from flowback.group.selectors import group_delegate_pool_comment_list
from flowback.group.services.delegate import (group_delegate_pool_comment_create,
                                              group_delegate_pool_comment_update,
                                              group_delegate_pool_comment_delete,
                                              group_delegate_pool_comment_vote)


class GroupDelegatePoolCommentListAPI(CommentListAPI):
    lazy_action = group_delegate_pool_comment_list


class GroupDelegatePoolCommentCreateAPI(CommentCreateAPI):
    lazy_action = group_delegate_pool_comment_create


class GroupDelegatePoolCommentUpdateAPI(CommentUpdateAPI):
    lazy_action = group_delegate_pool_comment_update


class GroupDelegatePoolCommentDeleteAPI(CommentDeleteAPI):
    lazy_action = group_delegate_pool_comment_delete


class GroupDelegatePoolCommentVoteAPI(CommentVoteAPI):
    lazy_action = group_delegate_pool_comment_vote
