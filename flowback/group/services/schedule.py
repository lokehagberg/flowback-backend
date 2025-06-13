from flowback.group.notify import notify_group_schedule_event
from flowback.group.selectors.permission import group_user_permissions
from flowback.notification.models import NotificationChannel
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

    notify_group_schedule_event(message="A new event has been created",
                                action=NotificationChannel.Action.CREATED,
                                schedule_event=event)

    if event.assignees:
        notify_group_schedule_event(message="You have been assigned to a new event",
                                    action=NotificationChannel.Action.CREATED,
                                    schedule_event=event,
                                    user_id_list=list(event.assignees.values_list('user_id', flat=True)))

    return event


def group_schedule_event_update(*,
                                user_id: int,
                                group_id: int,
                                event_id: int,
                                **data):
    old_event = group_schedule.get_schedule_event(event_id=event_id)
    old_event_assignees = list(old_event.assignees.values_list('user_id', flat=True))

    group_user = group_user_permissions(user=user_id,
                                        group=group_id,
                                        work_group=old_event.work_group.id if old_event.work_group else None)
    updated_event = group_schedule.update_event(event_id=event_id, schedule_origin_id=group_user.group.id, data=data)
    updated_event_assignees = list(updated_event.assignees.values_list('user_id', flat=True))

    # Notify users
    if list(set(old_event_assignees) - set(updated_event_assignees)):
        notify_group_schedule_event(message="You have been unassigned from an event",
                                    action=NotificationChannel.Action.UPDATED,
                                    schedule_event=updated_event,
                                    user_id_list=list(set(old_event_assignees) - set(updated_event_assignees)))

    if list(set(updated_event_assignees) - set(old_event_assignees)):
        notify_group_schedule_event(message="You have been assigned to an event",
                                    action=NotificationChannel.Action.UPDATED,
                                    schedule_event=updated_event,
                                    user_id_list=list(set(updated_event_assignees) - set(old_event_assignees)))


def group_schedule_event_delete(*,
                                user_id: int,
                                group_id: int,
                                event_id: int):
    event = group_schedule.get_schedule_event(event_id=event_id)
    group_user = group_user_permissions(user=user_id,
                                        group=group_id,
                                        work_group=event.work_group.id if event.work_group else None)
    group_schedule.delete_event(event_id=event_id, schedule_origin_id=group_user.group.id)

    if event.assignees:
        notify_group_schedule_event(message="The schedule event you've been assigned to has been deleted",
                                    action=NotificationChannel.Action.DELETED,
                                    schedule_event=event,
                                    user_id_list=list(event.assignees.values_list('user_id', flat=True)))


def group_schedule_subscribe(*,
                             user_id: int,
                             group_id: int):
    group_user = group_user_permissions(user=user_id, group=group_id)
    schedule = user_schedule.get_schedule(origin_id=user_id)
    target = group_user.group.schedule
    subscribe_schedule(schedule_id=schedule.id, target_id=target.id)
