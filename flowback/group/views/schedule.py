from flowback.schedule.views import (ScheduleEventLazyCreateAPI,
                                     ScheduleEventLazyUpdateAPI,
                                     ScheduleEventLazyDeleteAPI)
from flowback.group.services.group import (group_schedule_event_create,
                                           group_schedule_event_update,
                                           group_schedule_event_delete)
from flowback.group.services.workgroup import (work_group_schedule_event_create,
                                               work_group_schedule_event_update,
                                               work_group_schedule_event_delete)


class GroupScheduleEventCreateAPI(ScheduleEventLazyCreateAPI):
    lazy_action = group_schedule_event_create


class GroupScheduleEventUpdateAPI(ScheduleEventLazyUpdateAPI):
    lazy_action = group_schedule_event_update


class GroupScheduleEventDeleteAPI(ScheduleEventLazyDeleteAPI):
    lazy_action = group_schedule_event_delete


class WorkGroupScheduleEventCreateAPI(ScheduleEventLazyCreateAPI):
    lazy_action = work_group_schedule_event_create


class WorkGroupScheduleEventUpdateAPI(ScheduleEventLazyUpdateAPI):
    lazy_action = work_group_schedule_event_update


class WorkGroupScheduleEventDeleteAPI(ScheduleEventLazyDeleteAPI):
    lazy_action = work_group_schedule_event_delete
