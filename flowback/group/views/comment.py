from flowback.comment.views import CommentListAPI, CommentCreateAPI, CommentUpdateAPI, CommentDeleteAPI
from flowback.group.selectors import group_delegate_pool_comment_list
from flowback.group.services import (group_delegate_pool_comment_create,
                                     group_delegate_pool_comment_update,
                                     group_delegate_pool_comment_delete)


class GroupDelegatePoolCommentListAPI(CommentListAPI):
    lazy_action = group_delegate_pool_comment_list


class GroupDelegatePoolCommentCreateAPI(CommentCreateAPI):
    lazy_action = group_delegate_pool_comment_create


class GroupDelegatePoolCommentUpdateAPI(CommentUpdateAPI):
    lazy_action = group_delegate_pool_comment_update


class GroupDelegatePoolCommentDeleteAPI(CommentDeleteAPI):
    lazy_action = group_delegate_pool_comment_delete
