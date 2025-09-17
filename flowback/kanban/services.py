from flowback.common.services import get_object, model_update
from flowback.kanban.models import KanbanEntry
from flowback.group.selectors import group_user_permissions


def kanban_entry_create(*,
                        user_id: int,
                        group_id: int,
                        assignee_id: int,
                        title: str,
                        description: str,
                        tag: int) -> KanbanEntry:
    group_user_permissions(user=user_id, group=group_id)
    assignee = group_user_permissions(user=assignee_id, group=group_id)
    kanban = KanbanEntry(created_by_id=user_id, assignee_id=assignee.user.id,
                         title=title, description=description, tag=tag)

    kanban.full_clean()
    kanban.save()

    return kanban


def kanban_entry_update(*, fetched_by: int, group_id: int, kanban_entry_id: int, data) -> KanbanEntry:
    group_user_permissions(group=group_id, user=fetched_by)
    kanban = get_object(KanbanEntry, id=kanban_entry_id)

    if data.get('assignee_id'):
        data['assignee_id'] = group_user_permissions(group=group_id, user=data['assignee_id'])

    non_side_effect_fields = ['title', 'description', 'assignee', 'tag']

    kanban, has_updated = model_update(instance=kanban,
                                       fields=non_side_effect_fields,
                                       data=data)

    return kanban


def kanban_entry_delete(*, fetched_by: int, group_id: int, kanban_entry_id: int) -> None:
    group_user_permissions(group=group_id, user=fetched_by)
    kanban = get_object(KanbanEntry, id=kanban_entry_id).delete()

    kanban.delete()
