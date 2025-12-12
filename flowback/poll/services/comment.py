from flowback.comment.models import Comment
from flowback.common.services import get_object
from flowback.group.selectors.permission import group_user_permissions
from flowback.notification.models import NotificationChannel
from flowback.poll.models import Poll
from flowback.comment.services import comment_create, comment_update, comment_delete, comment_vote
from flowback.poll.notify import notify_poll_comment


def poll_comment_create(*, author_id: int, poll_id: int, message: str = None, attachments: list = None,
                        parent_id: int = None) -> Comment:
    poll = get_object(Poll, id=poll_id, active=True)
    group_user = group_user_permissions(user=author_id, group=poll.created_by.group.id)

    comment = comment_create(author_id=author_id,
                             comment_section_id=poll.comment_section.id,
                             message=message,
                             parent_id=parent_id,
                             attachments=attachments,
                             attachment_upload_to="group/poll/comment/attachments")

    notify_poll_comment(message="A new comment has been posted",
                        action=NotificationChannel.Action.CREATED,
                        poll=poll,
                        comment=comment)

    return comment


def poll_comment_update(*, fetched_by: int, poll_id: int, comment_id: int, data) -> Comment:
    poll = get_object(Poll, id=poll_id, active=True)
    group_user_permissions(user=fetched_by, group=poll.created_by.group.id)

    return comment_update(fetched_by=fetched_by,
                          comment_section_id=poll.comment_section.id,
                          comment_id=comment_id,
                          attachment_upload_to="group/poll/comment/attachments",
                          data=data)


def poll_comment_delete(*, fetched_by: int, poll_id: int, comment_id: int):
    poll = get_object(Poll, id=poll_id, active=True)

    force = bool(group_user_permissions(user=fetched_by,
                                        group=poll.created_by.group,
                                        permissions=['admin', 'force_delete_comment'],
                                        raise_exception=False))

    return comment_delete(fetched_by=fetched_by,
                          comment_section_id=poll.comment_section.id,
                          comment_id=comment_id,
                          force=force)


def poll_comment_vote(*, fetched_by: int, poll_id: int, comment_id: int, vote: bool = None):
    poll = Poll.objects.get(id=poll_id, active=True)
    group_user_permissions(user=fetched_by, group=poll.created_by.group)

    return comment_vote(fetched_by=fetched_by,
                        comment_section_id=poll.comment_section_id,
                        comment_id=comment_id,
                        vote=vote)
