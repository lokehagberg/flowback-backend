from flowback.comment.models import Comment
from flowback.notification.models import NotificationChannel, NotificationObject
from flowback.poll.models import Poll


def notify_poll(message: str,
                action: NotificationChannel.Action,
                poll: Poll) -> NotificationObject:
    users = None
    if poll.work_group:
        users = list(poll.work_group.group_users.values_list('user_id', flat=True))

    return poll.notify_poll(message=message,
                            action=action,
                            work_group_id=poll.work_group_id
                            if poll.work_group else None,
                            work_group_name=poll.work_group.name
                            if poll.work_group else None,
                            subscription_filters=dict(user_id__in=users) if users else None)


# TODO add notifications to every phase change
def notify_poll_phase(message: str,
                      action: NotificationChannel.Action,
                      poll: Poll) -> NotificationObject:
    users = None
    if poll.work_group:
        users = list(poll.work_group.group_users.values_list('user_id', flat=True))

    return poll.notify_poll_phase(message=message,
                                  action=action,
                                  work_group_id=poll.work_group_id
                                  if poll.work_group else None,
                                  work_group_name=poll.work_group.name
                                  if poll.work_group else None,
                                  current_phase=poll.current_phase.replace('_', ' ').capitalize(),
                                  subscription_filters=dict(user_id__in=users) if users else None)


def notify_poll_comment(message: str,
                        action: NotificationChannel.Action,
                        poll: Poll,
                        comment: Comment) -> NotificationObject:
    users = None
    if poll.work_group:
        users = list(poll.work_group.group_users.values_list('user_id', flat=True))

    return poll.notify_poll_comment(message=message,
                                    action=action,
                                    work_group_id=poll.work_group_id
                                    if poll.work_group else None,
                                    work_group_name=poll.work_group.name
                                    if poll.work_group else None,
                                    comment_message=comment.message,
                                    subscription_filters=dict(user_id__in=users) if users else None,
                                    exclude_subscription_filters=dict(user_id=comment.author_id))

