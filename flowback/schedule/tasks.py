# TODO Create task for reminders, one task per event should be enough, repeat or not (make another task, delete previous, update the new task with new timestamp, and save the id to database)
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.utils.datetime_safe import datetime
from django_celery_beat.models import PeriodicTask

from flowback.notification.services import NotificationManager
from flowback.schedule.models import ScheduleEvent

schedule_notification = NotificationManager(sender_type="schedule")

@shared_task
def event_notify(event_id: int, seconds_before_event: int = None):
    """
    :param event_id:  ScheduleEvent id
    :param seconds_before_event:  Purely visual, additional data for notification message
    """
    event = ScheduleEvent.objects.get(id=event_id)

    if not seconds_before_event:
        message = f'The event "{event.title}" has begun!'

    else:
        message = (f'The event "{event.title}" begins in '
                   f'{"{:0>8}".format(str(timedelta(seconds=seconds_before_event)))}!')

        schedule_notification.create(sender_id=event.schedule.id,
                                     action='info',
                                     category='event',
                                     message=message,
                                     related_id=event.id)

    # event = ScheduleEvent.objects.get(id=event_id)
    #
    # if not event.repeat_frequency:
    #     # Notify and return
    #     return
    #
    # current_date = timezone.now()
    #
    # if current_date.day >= 29:
    #     return
    #
    # if event.start_date > current_date:
    #     # Set the next event notification to start_date
    #     return
    #
    #
    # # When daily, shift to next day
    # if event.repeat_frequency == event.Frequency.DAILY:
    #     next_event = event.repeat_next_run + timedelta(days=1)
    #
    # # When weekly, shift to same day, next week
    # elif event.repeat_frequency == event.Frequency.WEEKLY:
    #     next_event = event.repeat_next_run + timedelta(weeks=1)
    #
    # # When monthly, shift to same day, next month (29th and higher will be skipped)
    # elif event.repeat_frequency == event.Frequency.MONTHLY:
    #     next_event = event.repeat_next_run
    #     next_event.replace(month=event.repeat_next_run.month + 1 if event.repeat_next_run.month < 12 else 1)
    #
    # else:
    #     raise ValueError(f"Unknown repeat_frequency: {event.repeat_frequency}")
    #
    # # When monthly, shift to same day, next month (29th and higher will be skipped)
    # next_event.replace(hour=event.start_date.hour,
    #                    minute=event.start_date.minute,
    #                    second=event.start_date.second,
    #                    microsecond=event.start_date.microsecond)
    #
    # event.repeat_next_run = next_event
    # event.save()


# TODO Delete task