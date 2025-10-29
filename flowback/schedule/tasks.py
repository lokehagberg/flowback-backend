from celery import shared_task
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from flowback.schedule.models import ScheduleEvent


@shared_task
def event_notify(event_id: int):
    """
    :param event_id:  ScheduleEvent id
    """
    event = ScheduleEvent.objects.get(id=event_id)

    # Skip notify if scheduled at a later date
    if event.start_date > timezone.now():
        return

    # Stop notifying if scheduled after end_date
    if not event or not event.repeat_frequency or (event.end_date and event.end_date < timezone.now()):
        PeriodicTask.objects.filter(name=f"schedule_event_{event_id}").delete()

    if event.repeat_frequency:
        event.regenerate_notifications()
