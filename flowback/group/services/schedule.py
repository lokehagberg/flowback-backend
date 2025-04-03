from django.utils import timezone

from flowback.group.models import WorkGroupUser
from flowback.group.selectors import group_user_permissions
from flowback.group.services.group import group_notification
from flowback.schedule.models import ScheduleEvent
from flowback.schedule.services import ScheduleManager, subscribe_schedule
from flowback.user.services import user_schedule

group_schedule = ScheduleManager(schedule_origin_name='group', possible_origins=['poll'])


def group_schedule_event_create(*,
                                user_id: int,
                                group_id: int,
                                title: str,
                                work_group_id: int = None,
                                **data) -> ScheduleEvent:
    group_user = group_user_permissions(user=user_id, group=group_id, work_group=work_group_id)
    event = group_schedule.create_event(schedule_id=group_user.group.schedule.id,
                                        title=title,
                                        origin_id=group_user.group.id,
                                        origin_name='group',
                                        work_group_id=work_group_id,
                                        **data)

    target_user_ids = None
    if work_group_id:
        target_user_ids = WorkGroupUser.objects.filter(id=work_group_id).values_list('group_user__user_id',
                                                                                     flat=True)

    group_notification.create(sender_id=group_id,
                              action=group_notification.Action.create,
                              category='schedule_event_create',
                              message='A new schedule event has been created',
                              related_id=event.id,
                              target_user_ids=list(target_user_ids))

    return event


def group_schedule_event_update(*,
                                user_id: int,
                                group_id: int,
                                event_id: int,
                                **data):
    work_group = group_schedule.get_schedule_event(event_id=event_id).work_group
    group_user = group_user_permissions(user=user_id, group=group_id, work_group=work_group.id if work_group else None)
    group_schedule.update_event(event_id=event_id, schedule_origin_id=group_user.group.id, data=data)

    target_user_ids = None
    if work_group:
        target_user_ids = WorkGroupUser.objects.filter(id=work_group.id).values_list('group_user__user_id',
                                                                                     flat=True)

    group_notification.create(sender_id=group_id,
                              action=group_notification.Action.update,
                              category='schedule_event_update',
                              message='A schedule event has been updated',
                              related_id=event_id,
                              target_user_ids=list(target_user_ids))


def group_schedule_event_delete(*,
                                user_id: int,
                                group_id: int,
                                event_id: int):
    work_group = group_schedule.get_schedule_event(event_id=event_id).work_group
    group_user = group_user_permissions(user=user_id, group=group_id, work_group=work_group.id if work_group else None)
    group_schedule.delete_event(event_id=event_id, schedule_origin_id=group_user.group.id)

    target_user_ids = None
    if work_group:
        target_user_ids = WorkGroupUser.objects.filter(id=work_group.id).values_list('group_user__user_id',
                                                                                     flat=True)

    group_notification.create(sender_id=group_id,
                              action=group_notification.Action.delete,
                              category='schedule_event_delete',
                              message='A schedule event has been deleted',
                              related_id=event_id,
                              target_user_ids=list(target_user_ids))


def group_schedule_subscribe(*,
                             user_id: int,
                             group_id: int):
    group_user = group_user_permissions(user=user_id, group=group_id)
    schedule = user_schedule.get_schedule(origin_id=user_id)
    target = group_user.group.schedule
    subscribe_schedule(schedule_id=schedule.id, target_id=target.id)
