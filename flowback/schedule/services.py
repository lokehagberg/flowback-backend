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
def schedule_notification_subscribe(*,
                                    user,
                                    schedule_id: int = None,
                                    event_id: int = None,
                                    user_tags: list[str] = None,
                                    locked: bool = True,
                                    tags: list[str] = None):
    """
    Subscribes user to either a schedule, a tag or an event.
    :param user: The user that'll subscribe
    :param schedule_id: The ID of the schedule to subscribe to,
     used for validation if at least one other field is filled.
     If schedule_id is the only field set, subscribes to all tags.
    :param event_id: The ID of the event to subscribe to. Takes priority over schedule and tag subscriptions.
     Will cause the event subscription to be locked.
    :param user_tags: List of user-defined tags to subscribe to.
    :param locked: Whether the event subscription should be locked. Only used for event_id subscriptions.
    :param tags: List of tags to subscribe to.
    :return:
    """
    if event_id:
        event = ScheduleEvent.objects.get(id=event_id)

        if schedule_id and event.schedule_id != schedule_id:
            raise ValidationError('Event does not belong to the schedule')

        event.event_subscribe(user=user,
                              user_tags=user_tags,
                              locked=locked)
    pass

# Unsubscribe
def schedule_notification_unsubscribe(*,
                                      user,
                                      schedule_id: int = None,
                                      event_id: int = None,
                                      tags: list[str] = None):
    """
    Unsubscribes the user from a schedule, tag or event.
    :param user: The user that'll unsubscribe
    :param schedule_id: The ID of the schedule to unsubscribe from. Used for validation.
     If schedule_id is the only field set, unsubscribes from all tags.
    :param event_id: The ID of the event to unsubscribe from.
    :param tags: The tags to unsubscribe from.
    """
    pass
# Update user event (user_tags, locked, reminders)
