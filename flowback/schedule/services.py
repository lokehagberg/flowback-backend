from django.utils import timezone
from rest_framework.exceptions import ValidationError

from flowback.common.services import model_update, get_object
from flowback.group.models import GroupUser
from flowback.schedule.models import Schedule, ScheduleEvent, ScheduleSubscription


def create_schedule(*, name: str, origin_name: str, origin_id: int) -> Schedule:
    schedule = Schedule(name=name, origin_name=origin_name, origin_id=origin_id)
    schedule.full_clean()
    schedule.save()

    return schedule


def update_schedule(*, schedule_id: int, data) -> Schedule:
    schedule = get_object(Schedule, id=schedule_id)
    non_side_effect_fields = ['name']
    schedule, has_updated = model_update(instance=schedule,
                                         fields=non_side_effect_fields,
                                         data=data)
    return schedule


def delete_schedule(*, schedule_id: int):
    schedule = get_object(Schedule, id=schedule_id)
    schedule.delete()


def create_event(*,
                 schedule_id: int,
                 title: str,
                 start_date: timezone.datetime,
                 end_date: timezone.datetime,
                 origin_name: str,
                 origin_id: int,
                 description: str = None,
                 work_group_id: int = None,
                 assignee_ids: list[int] = None) -> ScheduleEvent:
    schedule = Schedule.objects.get(id=schedule_id)

    # Simple hack to allow assignees for schedules, needs refactor in future
    if assignee_ids and schedule.origin_name == "group":
        assignees = GroupUser.objects.filter(id__in=assignee_ids)
        assignees = assignees.filter(group=assignees.first().group)
        if assignees.count() != len(assignee_ids):
            raise ValidationError("Not all assignees are assignable to this event.")

    event = ScheduleEvent(schedule_id=schedule_id,
                          title=title,
                          description=description,
                          start_date=start_date,
                          end_date=end_date,
                          origin_name=origin_name,
                          work_group_id=work_group_id,
                          origin_id=origin_id)
    event.full_clean()
    event.save()

    if assignee_ids and schedule.origin_name == "group":
        event.assignees.add(*assignee_ids)

    elif assignee_ids and not event.schedule.origin_name == "group":
        raise ValidationError("Assignees are only available for groups.")

    return event


def update_event(*, event_id: int, data) -> ScheduleEvent:
    event = ScheduleEvent.objects.get(id=event_id)

    non_side_effect_fields = ['title', 'description', 'start_date', 'end_date']
    event, has_updated = model_update(instance=event,
                                      fields=non_side_effect_fields,
                                      data=data)

    # Simple hack to allow assignees for schedules, needs refactor in future
    if 'assignee_ids' in data.keys() and event.schedule.origin_name == "group":
        assignee_ids = data.pop('assignee_ids')

        assignees = GroupUser.objects.filter(id__in=assignee_ids)
        assignees = assignees.filter(group=assignees.first().group)
        if assignees.count() != len(assignee_ids):
            raise ValidationError("Not all assignees are assignable to this event.")

        event.assignees.clear()
        event.assignees.add(*assignees)

    elif 'assignee_ids' in data.keys() and not event.schedule.origin_name == "group":
        raise ValidationError("Assignees are only available for groups.")

    return event


def delete_event(*, event_id: int):
    event = get_object(ScheduleEvent, id=event_id)
    event.delete()


def subscribe_schedule(*, schedule_id: int, target_id: int) -> ScheduleSubscription:
    subscription = ScheduleSubscription(schedule_id=schedule_id, target_id=target_id)
    subscription.full_clean()
    return subscription.save()


def unsubscribe_schedule(*, schedule_id: int, target_id: int):
    subscription = get_object(ScheduleSubscription, schedule_id=schedule_id, target_id=target_id)
    subscription.delete()


class ScheduleManager:
    def __init__(self, schedule_origin_name: str, possible_origins: list[str] = None):
        self.origin_name = schedule_origin_name
        self.possible_origins = possible_origins or []

        if self.origin_name not in self.possible_origins:
            self.possible_origins.append(self.origin_name)

    def validate_origin_name(self, origin_name: str):
        if origin_name not in self.possible_origins:
            raise Exception('origin_name not in possible_origins')

    # Schedule
    def get_schedule(self, *, origin_name: str = None, origin_id: int) -> Schedule:
        return get_object(Schedule, origin_name=origin_name or self.origin_name,
                          origin_id=origin_id)

    def create_schedule(self, *, name: str, origin_id: int) -> Schedule:
        get_object(Schedule, origin_name=self.origin_name, origin_id=origin_id, reverse=True)
        return create_schedule(name=name, origin_name=self.origin_name, origin_id=origin_id)

    def update_schedule(self, *, origin_id: int, data):
        schedule = self.get_schedule(origin_id=origin_id)
        update_schedule(schedule_id=schedule.id, data=data)

    def delete_schedule(self, origin_id: int):
        schedule = self.get_schedule(origin_id=origin_id)
        delete_schedule(schedule_id=schedule.id)

    # Event
    def get_schedule_event(self,
                           event_id: int,
                           schedule_origin_id: int = None,
                           raise_exception: bool = True) -> ScheduleEvent:
        data = dict(id=event_id,
                    schedule__origin_name=self.origin_name,
                    raise_exception=raise_exception)

        if schedule_origin_id is not None:
            data['schedule_origin_id'] = schedule_origin_id

        return get_object(ScheduleEvent, **data)

    def create_event(self,
                     *,
                     schedule_id: int,
                     title: str,
                     start_date: timezone.datetime,
                     end_date: timezone.datetime,
                     origin_name: str,
                     origin_id: int,
                     description: str = None,
                     work_group_id: int = None,
                     assignee_ids: list[int] = None) -> ScheduleEvent:

        self.validate_origin_name(origin_name=origin_name)

        return create_event(schedule_id=schedule_id,
                            title=title,
                            start_date=start_date,
                            end_date=end_date,
                            origin_name=origin_name,
                            origin_id=origin_id,
                            work_group_id=work_group_id,
                            description=description,
                            assignee_ids=assignee_ids)

    def update_event(self, *, schedule_origin_id: int, event_id: int, data):
        get_object(ScheduleEvent, id=event_id,
                   schedule__origin_id=schedule_origin_id,
                   schedule__origin_name=self.origin_name)
        update_event(event_id=event_id, data=data)

    def delete_event(self, *, schedule_origin_id: int, event_id: int):
        get_object(ScheduleEvent, id=event_id,
                   schedule__origin_id=schedule_origin_id,
                   schedule__origin_name=self.origin_name)
        delete_event(event_id=event_id)
