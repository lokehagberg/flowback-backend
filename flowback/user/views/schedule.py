from flowback.schedule.views import (ScheduleEventLazyCreateAPI,
                                     ScheduleEventLazyUpdateAPI,
                                     ScheduleEventLazyDeleteAPI)
from flowback.user.services import (user_schedule_event_create,
                                    user_schedule_event_update,
                                    user_schedule_event_delete)


class UserScheduleEventCreateAPI(ScheduleEventLazyCreateAPI):
    lazy_action = user_schedule_event_create


class UserScheduleEventUpdateAPI(ScheduleEventLazyUpdateAPI):
    lazy_action = user_schedule_event_update


class UserScheduleEventDeleteAPI(ScheduleEventLazyDeleteAPI):
    lazy_action = user_schedule_event_delete
