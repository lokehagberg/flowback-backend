from celery import shared_task
from django_celery_beat.models import PeriodicTask

from flowback.schedule.models import ScheduleEvent


@shared_task
def event_notify(event_id: int):
    """
    :param event_id:  ScheduleEvent id
    """
    event = ScheduleEvent.objects.get(id=event_id)

    if not event or not event.repeat_frequency:
        PeriodicTask.objects.filter(name=f"schedule_event_{event_id}").delete()

    if event.repeat_frequency:
        event.regenerate_notifications()
