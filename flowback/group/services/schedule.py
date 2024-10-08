from django.utils import timezone

from flowback.group.selectors import group_user_permissions
from flowback.schedule.models import ScheduleEvent
from flowback.schedule.services import ScheduleManager, subscribe_schedule
from flowback.user.services import user_schedule

group_schedule = ScheduleManager(schedule_origin_name='group', possible_origins=['poll'])


def group_schedule_event_create(*,
                                user_id: int,
                                group_id: int,
                                title: str,
                                start_date: timezone.datetime,
                                description: str = None,
                                work_group_id: int = None,
                                end_date: timezone.datetime = None) -> ScheduleEvent:
    group_user = group_user_permissions(user=user_id, group=group_id, work_group=work_group_id)
    return group_schedule.create_event(schedule_id=group_user.group.schedule.id,
                                       title=title,
                                       start_date=start_date,
                                       end_date=end_date,
                                       origin_id=group_user.group.id,
                                       origin_name='group',
                                       work_group_id=work_group_id,
                                       description=description)


def group_schedule_event_update(*,
                                user_id: int,
                                group_id: int,
                                event_id: int,
                                **data):
    work_group = group_schedule.get_schedule_event(event_id=event_id).work_group
    group_user = group_user_permissions(user=user_id, group=group_id, work_group=work_group.id if work_group else None)
    group_schedule.update_event(event_id=event_id, schedule_origin_id=group_user.group.id, data=data)


def group_schedule_event_delete(*,
                                user_id: int,
                                group_id: int,
                                event_id: int):
    work_group = group_schedule.get_schedule_event(event_id=event_id).work_group
    group_user = group_user_permissions(user=user_id, group=group_id, work_group=work_group.id if work_group else None)
    group_schedule.delete_event(event_id=event_id, schedule_origin_id=group_user.group.id)


def group_schedule_subscribe(*,
                             user_id: int,
                             group_id: int):
    group_user = group_user_permissions(user=user_id, group=group_id)
    schedule = user_schedule.get_schedule(origin_id=user_id)
    target = group_user.group.schedule
    subscribe_schedule(schedule_id=schedule.id, target_id=target.id)
