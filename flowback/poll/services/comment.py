from flowback.comment.models import Comment
from flowback.common.services import get_object
from flowback.group.selectors import group_user_permissions
from flowback.poll.models import Poll, PollDelegateVoting
from flowback.comment.services import comment_create, comment_update, comment_delete, comment_vote
from flowback.poll.services.poll import poll_notification


def poll_comment_create(*, author_id: int, poll_id: int, message: str = None, attachments: list = None,
                        parent_id: int = None) -> Comment:
    poll = get_object(Poll, id=poll_id)
    group_user = group_user_permissions(user=author_id, group=poll.created_by.group.id)

    comment = comment_create(author_id=author_id,
                             comment_section_id=poll.comment_section.id,
                             message=message,
                             parent_id=parent_id,
                             attachments=attachments,
                             attachment_upload_to="group/poll/comment/attachments")

    poll_notification.create(sender_id=poll_id,
                             action=poll_notification.Action.create,
                             category='comment_all',
                             message=f'User {group_user.user.username} replied to your comment '
                                     f'in poll {poll.title}',
                             related_id=comment.id)

    if poll_notification.is_subscribed(user_id=comment.author_id, sender_id=poll_id, category='comment_self'):
        poll_notification.create(sender_id=poll_id,
                                 action=poll_notification.Action.create,
                                 category='comment_self',
                                 message=f'User {group_user.user.username} replied to your comment '
                                         f'in poll {poll.title}',
                                 related_id=comment.id,
                                 target_user_id=comment.author_id)

    return comment


def poll_comment_update(*, fetched_by: int, poll_id: int, comment_id: int, data) -> Comment:
    poll = get_object(Poll, id=poll_id)
    group_user_permissions(user=fetched_by, group=poll.created_by.group.id)

    return comment_update(fetched_by=fetched_by,
                          comment_section_id=poll.comment_section.id,
                          comment_id=comment_id,
                          data=data)


def poll_comment_delete(*, fetched_by: int, poll_id: int, comment_id: int):
    poll = get_object(Poll, id=poll_id)

    force = bool(group_user_permissions(user=fetched_by,
                                        group=poll.created_by.group,
                                        permissions=['admin', 'force_delete_comment'],
                                        raise_exception=False))

    return comment_delete(fetched_by=fetched_by,
                          comment_section_id=poll.comment_section.id,
                          comment_id=comment_id,
                          force=force)


def poll_comment_vote(*, fetched_by: int, poll_id: int, comment_id: int, vote: bool = None):
    poll = Poll.objects.get(id=poll_id)
    group_user_permissions(user=fetched_by, group=poll.created_by.group)

    return comment_vote(fetched_by=fetched_by,
                        comment_section_id=poll.comment_section_id,
                        comment_id=comment_id,
                        vote=vote)
