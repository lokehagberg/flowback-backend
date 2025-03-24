from django.utils import timezone

from flowback.group.selectors import group_user_permissions
from flowback.group.services.group import group_notification
from flowback.kanban.models import KanbanEntry
from flowback.kanban.services import KanbanManager

group_kanban = KanbanManager(origin_type='group')


def group_kanban_entry_create(*,
                              group_id: int,
                              fetched_by_id: int,
                              assignee_id: int = None,
                              title: str,
                              description: str = None,
                              priority: int,
                              lane: int,
                              work_group_id: int = None,
                              attachments: list = None,
                              end_date: timezone.datetime = None
                              ) -> KanbanEntry:
    group_user = group_user_permissions(user=fetched_by_id,
                                        group=group_id,
                                        permissions=['admin', 'create_kanban_task'],
                                        work_group=work_group_id)
    kanban = group_kanban.kanban_entry_create(origin_id=group_id,
                                              created_by_id=fetched_by_id,
                                              assignee_id=assignee_id,
                                              title=title,
                                              description=description,
                                              attachments=attachments,
                                              work_group_id=work_group_id,
                                              priority=priority,
                                              end_date=end_date,
                                              lane=lane)

    group_notification.create(sender_id=group_id, action=group_notification.Action.create, category='kanban',
                              message=f'User {group_user.user.username} created a kanban in {group_user.group.name}')

    return kanban


def group_kanban_entry_update(*,
                              fetched_by_id: int,
                              group_id: int,
                              entry_id: int,
                              data) -> KanbanEntry:
    work_group = KanbanEntry.objects.get(id=entry_id).work_group
    group_user = group_user_permissions(user=fetched_by_id,
                                        group=group_id,
                                        permissions=['admin', 'update_kanban_task'],
                                        work_group=work_group.id if work_group else None)

    if 'assignee_id' in data.keys() and data['assignee_id'] is not None:
        group_user_permissions(user=data['assignee_id'], group=group_id)

    kanban = group_kanban.kanban_entry_update(origin_id=group_id,
                                              entry_id=entry_id,
                                              data=data)

    if 'assignee_id' in data.keys() and data['assignee_id'] is not None:  # Notify assignee about kanban
        group_notification.create(sender_id=group_id, related_id=entry_id,
                                  action=group_notification.Action.update, category='kanban_self_assign',
                                  message=f'You have been assigned to a kanban in {group_user.group.name}',
                                  target_user_ids=data['assignee_id'])

    for check in ['lane', 'priority']:
        if check in data.keys() and data[check] is not None:  # Notify status update
            group_notification.create(sender_id=group_id, related_id=entry_id,
                                      action=group_notification.Action.update, category=f'kanban_{check}_update',
                                      message=f'Status for {check} "{kanban.title}" has been updated',
                                      target_user_ids=data['assignee_id'])

    return kanban


def group_kanban_entry_delete(*,
                              fetched_by_id: int,
                              group_id: int,
                              entry_id: int):
    work_group = KanbanEntry.objects.get(id=entry_id).work_group
    group_user_permissions(user=fetched_by_id,
                           group=group_id,
                           permissions=['admin', 'delete_kanban_task'],
                           work_group=work_group.id if work_group else None)
    return group_kanban.kanban_entry_delete(origin_id=group_id, entry_id=entry_id)
