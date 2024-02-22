from flowback.comment.selectors import comment_list
from flowback.common.services import get_object
from flowback.poll.models import Poll, PollDelegateVoting
from flowback.user.models import User
from flowback.group.selectors import group_user_permissions


def poll_comment_list(*, fetched_by: User, poll_id: int, filters=None):
    filters = filters or {}

    poll = get_object(Poll, id=poll_id)
    group_user_permissions(group=poll.created_by.group.id, user=fetched_by)

    return comment_list(fetched_by=fetched_by, comment_section_id=poll.comment_section.id, filters=filters)


def poll_delegate_comment_list(*, fetched_by: User, poll_id: int, delegate_pool_id: int, filters=None):
    delegate_vote = get_object(PollDelegateVoting, poll_id=poll_id, created_by_id=delegate_pool_id)
    filters = filters or {}

    group_user_permissions(group=delegate_vote.created_by.group.id, user=fetched_by)

    return comment_list(fetched_by=fetched_by, comment_section_id=delegate_vote.comment_section.id, filters=filters)
