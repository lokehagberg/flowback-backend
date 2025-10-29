import datetime

from django.core.exceptions import ValidationError

from flowback.common.services import model_update
from flowback.schedule.models import Schedule, ScheduleTag, ScheduleEvent


# Create event
def create_event(*,
                 schedule_id: int,
                 title: str,
                 description: str = None,
                 start_date: datetime.datetime,
                 end_date: datetime.datetime = None,
                 created_by=None,
                 tag: str = None,
                 assignees: list[int] = None,
                 meeting_link: str = None,
                 repeat_frequency: int = None) -> ScheduleEvent:
    fields = locals()

    schedule = Schedule.objects.get(id=schedule_id)
    return schedule.create_event(**fields)


# Update event
def update_event(*,
                 event_id: int,
                 schedule_id: int = None,
                 **data) -> ScheduleEvent:
    """
    Updates an event
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
                              'repeat_frequency',
                              'assignees']

    event, updated = model_update(instance=event,
                                  fields=non_side_effect_fields,
                                  data=data)

    return event


# Delete event
def delete_event(*,
                 event_id: int,
                 schedule_id: int = None) -> None:
    """
    Deletes an event
    :param event_id: Event to remove
    :param schedule_id: Schedule id (for validation)
    :return: None
    """
    event = ScheduleEvent.objects.get(id=event_id)

    if not event.schedule_id == schedule_id:
        raise ValidationError("Event does not belong to the schedule")

    event.delete()

# Subscribe (incl. tags, user tags)
# Unsubscribe
# Update user event (user_tags, locked, reminders)
