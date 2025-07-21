from django.utils import timezone

from flowback.group.notify import notify_group_kanban
from flowback.group.selectors.permission import group_user_permissions
from flowback.kanban.models import KanbanEntry
from flowback.kanban.services import KanbanManager
from flowback.notification.models import NotificationChannel

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

    notify_group_kanban(kanban_entry=kanban,
                        message="New kanban entry has been created",
                        action=NotificationChannel.Action.CREATED)

    if assignee_id:
        notify_group_kanban(kanban_entry=kanban,
                            message="New kanban entry has been assigned to you",
                            user=assignee_id,
                            action=NotificationChannel.Action.CREATED)

    return kanban


def group_kanban_entry_update(*,
                              fetched_by_id: int,
                              group_id: int,
                              entry_id: int,
                              data) -> KanbanEntry:
    previous_kanban_entry = KanbanEntry.objects.get(id=entry_id,
                                                    kanban__origin_type='group',
                                                    kanban__origin_id=group_id)

    group_user = group_user_permissions(user=fetched_by_id,
                                        group=group_id,
                                        permissions=['admin', 'update_kanban_task'],
                                        work_group=previous_kanban_entry.work_group.id
                                        if previous_kanban_entry.work_group else None)

    if 'assignee_id' in data.keys() and data['assignee_id'] is not None:
        group_user_permissions(user=data['assignee_id'], group=group_id)
        
    if not data.get("work_group_id"):
        data["work_group_id"] = None
    
    new_kanban_entry = group_kanban.kanban_entry_update(origin_id=group_id,
                                              entry_id=entry_id,
                                              data=data)

    # Notify Users
    if data.get('assignee_id', None) and data['assignee_id'] != previous_kanban_entry.assignee_id:
        notify_group_kanban(kanban_entry=new_kanban_entry,
                            message="A kanban entry has been assigned to you",
                            user=data['assignee_id'],
                            action=NotificationChannel.Action.UPDATED)

        if previous_kanban_entry.assignee_id:
            notify_group_kanban(kanban_entry=new_kanban_entry,
                                message="You have been unassigned from a kanban entry",
                                user=previous_kanban_entry.assignee_id,
                                action=NotificationChannel.Action.UPDATED)

    elif new_kanban_entry.assignee_id:
        notify_group_kanban(kanban_entry=new_kanban_entry,
                            message="A kanban entry you've been assigned to has been updated",
                            user=new_kanban_entry.assignee_id,
                            action=NotificationChannel.Action.UPDATED)

    return new_kanban_entry


def group_kanban_entry_delete(*,
                              fetched_by_id: int,
                              group_id: int,
                              entry_id: int):
    kanban_entry = KanbanEntry.objects.get(id=entry_id, kanban__origin_type='group', kanban__origin_id=group_id)
    group_user_permissions(user=fetched_by_id,
                           group=group_id,
                           permissions=['admin', 'delete_kanban_task'],
                           work_group=kanban_entry.work_group.id if kanban_entry.work_group else None)

    if kanban_entry.assignee_id:
        notify_group_kanban(kanban_entry=kanban_entry,
                            message="A kanban entry you've been assigned to has been deleted",
                            user=kanban_entry.assignee_id,
                            action=NotificationChannel.Action.DELETED)

    return group_kanban.kanban_entry_delete(origin_id=group_id, entry_id=entry_id)
