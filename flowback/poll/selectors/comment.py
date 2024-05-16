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
