from django.urls import path

from flowback.schedule.views import (ScheduleListAPI,
                                      ScheduleEventListAPI,
                                      ScheduleSubscribeAPI,
                                      ScheduleUnsubscribeAPI,
                                      ScheduleEventSubscribeAPI,
                                      ScheduleEventUnsubscribeAPI,
                                      ScheduleTagSubscribeAPI,
                                      ScheduleTagUnsubscribeAPI)


schedule_patterns = [
    path('list', ScheduleListAPI.as_view(), name='schedule_list'),
    path('event/list', ScheduleEventListAPI.as_view(), name='schedule_event_list'),
    path('<int:schedule_id>/subscribe', ScheduleSubscribeAPI.as_view(), name='schedule_subscribe'),
    path('<int:schedule_id>/unsubscribe', ScheduleUnsubscribeAPI.as_view(), name='schedule_unsubscribe'),
    path('<int:schedule_id>/event/subscribe', ScheduleEventSubscribeAPI.as_view(), name='schedule_event_subscribe'),
    path('<int:schedule_id>/event/unsubscribe', ScheduleEventUnsubscribeAPI.as_view(), name='schedule_event_unsubscribe'),
    path('<int:schedule_id>/tag/subscribe', ScheduleTagSubscribeAPI.as_view(), name='schedule_tag_subscribe'),
    path('<int:schedule_id>/tag/unsubscribe', ScheduleTagUnsubscribeAPI.as_view(), name='schedule_tag_unsubscribe'),
]
