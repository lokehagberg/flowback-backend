from flowback.group.models import GroupThread, GroupUserDelegatePool, GroupUserDelegator
from flowback.poll.models import Poll
from flowback.kanban.models import KanbanEntry
from flowback.notification.models import NotificationChannel
from flowback.user.models import User


def notify_group_kanban(message: str,
                        action: NotificationChannel.Action,
                        kanban_entry: KanbanEntry,
                        user: User | int = None):
    user_id = user if isinstance(user, int) or user is None else user.id
    group = kanban_entry.kanban.group_set.first()

    users = [user_id] if user_id else None
    if kanban_entry.work_group and not users:
        users = kanban_entry.work_group.group_users.values_list('user_id', flat=True)

    return group.notify_kanban(message=message,
                               action=action,
                               kanban_entry_id=kanban_entry.id,
                               kanban_entry_title=kanban_entry.title,
                               work_group_id=kanban_entry.work_group_id
                               if kanban_entry.work_group else None,
                               work_group_name=kanban_entry.work_group.name
                               if kanban_entry.work_group else None,
                               subscription_filters=dict(user_id__in=users) if users else None)


def notify_group_thread(message: str,
                        action: NotificationChannel.Action,
                        thread: GroupThread):
    subscription_filters = None

    if thread.work_group:
        subscription_filters = dict(user_id__in=list(thread.work_group.group_users.values_list('user_id', flat=True)))

    return thread.created_by.group.notify_thread(message=message,
                                                 action=action,
                                                 thread_id=thread.id,
                                                 thread_title=thread.title,
                                                 work_group_id=thread.work_group_id if thread.work_group else None,
                                                 work_group_name=thread.work_group.name if thread.work_group else None,
                                                 subscription_filters=subscription_filters)


def notify_group_poll(message: str,
                      action: NotificationChannel.Action,
                      poll: Poll):
    subscription_filters = None

    if poll.work_group:
        subscription_filters = dict(user_id__in=list(poll.work_group.group_users.values_list('user_id', flat=True)))

    return poll.created_by.group.notify_poll(message=message,
                                             action=action,
                                             poll_id=poll.id,
                                             poll_title=poll.title,
                                             work_group_id=poll.work_group_id if poll.work_group else None,
                                             work_group_name=poll.work_group.name if poll.work_group else None,
                                             subscription_filters=subscription_filters)


def notify_group_user_delegate_pool_poll_vote_update(message: str,
                                                     action: NotificationChannel.Action,
                                                     delegate_pool: GroupUserDelegatePool,
                                                     poll: Poll):
    user_ids = list(GroupUserDelegator.objects.filter(delegate_pool=delegate_pool,
                                                      tags__in=[poll.tag]).values_list('delegator__user_id',
                                                                                       flat=True))

    delegate_pool.notify_poll_vote_update(action=action,
                                          message=message,
                                          poll_id=poll.id,
                                          poll_title=poll.title,
                                          subscription_filters=dict(user_id__in=user_ids))
