import datetime

from django.core.exceptions import ValidationError

from flowback.common.services import model_update
from flowback.schedule.models import Schedule, ScheduleEvent, ScheduleUser


def schedule_event_create(*,
                          schedule_id: int,
                          title: str,
                          description: str = None,
                          start_date: datetime.datetime,
                          end_date: datetime.datetime = None,
                          created_by=None,
                          tag: str = None,
                          assignees: list[int] = None,
                          meeting_link: str = None,
                          repeat_frequency: int = None,
                          **kwargs) -> ScheduleEvent:
    fields = locals()
    schedule = Schedule.objects.get(id=schedule_id)

    # Manual management of getting the group from created_by
    if assignees:
        group = None
        match schedule.content_type.model:
            case 'group':
                group = schedule.created_by
            case 'poll':
                group = schedule.created_by.created_by.group
            case 'workgroup':
                group = schedule.created_by.group

        if group is None:
            raise ValidationError("Assignees can only be assigned to events created by a group.")

        if not all([assignee.group == group for assignee in assignees.all()]):
            raise ValidationError("Not all group users are assignable to this event.")

    schedule = Schedule.objects.get(id=schedule_id)
    fields.pop('schedule_id')
    fields.pop('kwargs')

    return schedule.create_event(**fields)


def schedule_event_update(*,
                          event_id: int,
                          schedule_id: int = None,
                          **data) -> ScheduleEvent:
    """
    Updates an event
    :param user: Placeholder for lazy_action, won't do anything.
    :param event_id: The event id to update
    :param schedule_id: Schedule id (for validation)
    :param data: Update fields with data
    :return: ScheduleEvent object
    """
    event = ScheduleEvent.objects.get(id=event_id)

    if schedule_id and not event.schedule_id == schedule_id:
        raise ValidationError("Event does not belong to the schedule")

    non_side_effect_fields = ['title',
                              'description',
                              'start_date',
                              'end_date',
                              'tag',
                              'meeting_link',
                              'repeat_frequency']

    event, updated = model_update(instance=event,
                                  fields=non_side_effect_fields,
                                  data=data)

    if data.get('assignees'):
        event.assignees.set(data.get('assignees'))

    return event


def schedule_event_delete(*,
                          event_id: int,
                          schedule_id: int = None,
                          **kwargs) -> None:
    """
    Deletes an event
    :param user: Placeholder for lazy_action, won't do anything.
    :param event_id: Event to remove
    :param schedule_id: Schedule id (for validation)
    :return: None
    """
    event = ScheduleEvent.objects.get(id=event_id)

    if not event.schedule_id == schedule_id:
        raise ValidationError("Event does not belong to the schedule")

    event.delete()


# Subscription services
def schedule_event_subscribe(*, user,
                             schedule_id: int,
                             event_ids: list[int],
                             user_tags: list[str] = None,
                             locked: bool = True,
                             reminders: list[int] = None) -> None:
    schedule = Schedule.objects.get(id=schedule_id)
    schedule.subscribe_events(user=user,
                              event_ids=event_ids,
                              user_tags=user_tags,
                              reminders=reminders,
                              locked=locked)


def schedule_event_unsubscribe(*, user,
                               schedule_id: int,
                               event_ids: list[int]) -> None:
    schedule = Schedule.objects.get(id=schedule_id)
    schedule.unsubscribe_events(user=user, event_ids=event_ids)


def schedule_tag_subscribe(*, user,
                           schedule_id: int,
                           tag_ids: list[int],
                           reminders: list[int] = None) -> None:
    schedule = Schedule.objects.get(id=schedule_id)
    schedule.subscribe_tags(user=user, tag_ids=tag_ids, reminders=reminders)


def schedule_tag_unsubscribe(*, user,
                             schedule_id: int,
                             tag_ids: list[int]) -> None:
    schedule = Schedule.objects.get(id=schedule_id)
    schedule.unsubscribe_tags(user=user, tag_ids=tag_ids)


def schedule_subscribe_to_new_tags(*, user,
                                   schedule_id: int,
                                   reminders: list[int] = None) -> None:
    schedule_user = ScheduleUser.objects.get(schedule_id=schedule_id, user=user)
    schedule_user.subscribe_to_new_notification_tags = True
    schedule_user.reminders = reminders
    schedule_user.save()


def schedule_unsubscribe_to_new_tags(*, user,
                                     schedule_id: int) -> None:
    schedule_user = ScheduleUser.objects.get(schedule_id=schedule_id, user=user)
    schedule_user.subscribe_to_new_notification_tags = False
    schedule_user.reminders = None
    schedule_user.save()
