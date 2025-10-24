from django.shortcuts import get_object_or_404
from django.utils import timezone

from flowback.common.services import get_object, model_update
from flowback.files.services import upload_collection
from flowback.kanban.models import Kanban, KanbanSubscription, KanbanEntry


def kanban_create(*, name: str, origin_type: str, origin_id: int):
    kanban = Kanban(name=name, origin_type=origin_type, origin_id=origin_id)
    kanban.full_clean()
    kanban.save()

    return kanban


def kanban_delete(*, origin_type: str, origin_id: int):
    get_object(Kanban, origin_type=origin_type, origin_id=origin_id).delete()


def kanban_subscription_create(*, kanban_id: int, target_id: int) -> None:
    subscription = KanbanSubscription(kanban_id=kanban_id, target_id=target_id)
    subscription.full_clean()
    subscription.save()


def kanban_subscription_delete(*, kanban_id: int, target_id: int) -> None:
    get_object(KanbanSubscription, kanban_id=kanban_id, target_id=target_id).delete()


def kanban_entry_create(*,
                        kanban_id: int,
                        created_by_id: int,
                        title: str,
                        description: str,
                        lane: int,
                        priority: int,
                        assignee_id: int = None,
                        attachments: list = None,
                        work_group_id=None,
                        end_date: timezone.datetime = None) -> KanbanEntry:
    kanban = KanbanEntry(kanban_id=kanban_id,
                         created_by_id=created_by_id,
                         assignee_id=assignee_id,
                         title=title,
                         description=description,
                         lane=lane,
                         priority=priority,
                         work_group_id=work_group_id,
                         end_date=end_date)

    kanban.full_clean()

    if attachments:
        kanban.attachments = upload_collection(user_id=created_by_id,
                                               file=attachments,
                                               upload_to=f'kanban/task/{kanban_id}')

    kanban.save()

    return kanban


def kanban_entry_update(*, kanban_entry_id: int, data) -> KanbanEntry:
    kanban = get_object(KanbanEntry, id=kanban_entry_id)

    non_side_effect_fields = ['title', 'description', 'assignee_id', 'priority',
                              'lane', 'end_date', 'work_group_id', 'attachments']

    if 'attachments' in data.keys() and data['attachments']:
        data['attachments'] = upload_collection(user_id=kanban.created_by_id,
                                                file=data['attachments'],
                                                upload_to=f'kanban/task/{kanban.kanban_id}')

    kanban, has_updated = model_update(instance=kanban,
                                       fields=non_side_effect_fields,
                                       data=data)

    return kanban


def kanban_entry_delete(*, kanban_entry_id: int) -> None:
    get_object(KanbanEntry, id=kanban_entry_id).delete()


class KanbanManager:
    def __init__(self, origin_type: str):
        self.origin_type = origin_type

    def get_kanban(self, origin_id: int, origin_type: str = None):
        return get_object(Kanban, origin_type=origin_type or self.origin_type, origin_id=origin_id)

    def kanban_create(self, *, name: str, origin_id: int):
        get_object(Kanban, reverse=True, origin_name=self.origin_type, origin_id=origin_id)
        kanban_create(name=name, origin_type=self.origin_type, origin_id=origin_id)

    def kanban_delete(self, origin_id: int):
        kanban_delete(origin_type=self.origin_type, origin_id=origin_id)

    def kanban_subscription_create(self, *, origin_id: int, target_type: str, target_id: int):
        kanban = self.get_kanban(origin_id=origin_id)
        target = self.get_kanban(origin_type=target_type, origin_id=target_id)
        return kanban_subscription_create(kanban_id=kanban.id, target_id=target.id)

    def kanban_subscription_delete(self, *, origin_id: int, target_type: str, target_id: int):
        kanban = self.get_kanban(origin_id=origin_id)
        target = self.get_kanban(origin_type=target_type, origin_id=target_id)
        return kanban_subscription_delete(kanban_id=kanban.id, target_id=target.id)

    def get_entry(self, *, origin_id: int, entry_id: int):
        kanban = self.get_kanban(origin_id=origin_id)
        return get_object(KanbanEntry, id=entry_id, kanban_id=kanban.id)

    def kanban_entry_create(self,
                            *,
                            origin_id: int,
                            created_by_id: int,
                            assignee_id: int = None,
                            title: str,
                            description: str = None,
                            priority: int,
                            lane: int,
                            attachments: list = None,
                            work_group_id=None,
                            end_date: timezone.datetime = None) -> KanbanEntry:
        kanban = self.get_kanban(origin_id=origin_id)
        return kanban_entry_create(kanban_id=kanban.id,
                                   created_by_id=created_by_id,
                                   assignee_id=assignee_id,
                                   title=title,
                                   description=description,
                                   attachments=attachments,
                                   work_group_id=work_group_id,
                                   priority=priority,
                                   end_date=end_date,
                                   lane=lane, )

    def kanban_entry_update(self,
                            *,
                            origin_id: int,
                            entry_id: int,
                            data) -> KanbanEntry:
        self.get_entry(origin_id=origin_id, entry_id=entry_id)
        return kanban_entry_update(kanban_entry_id=entry_id, data=data)

    def kanban_entry_delete(self,
                            *,
                            origin_id: int,
                            entry_id: int):
        self.get_entry(origin_id=origin_id, entry_id=entry_id)
        return kanban_entry_delete(kanban_entry_id=entry_id)
