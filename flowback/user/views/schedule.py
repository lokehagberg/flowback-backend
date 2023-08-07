from rest_framework import status
from rest_framework.response import Response

from flowback.common.pagination import get_paginated_response
from flowback.schedule.views import (ScheduleEventListTemplateAPI,
                                     ScheduleEventCreateTemplateAPI,
                                     ScheduleEventUpdateTemplateAPI,
                                     ScheduleEventDeleteAPI, ScheduleUnsubscribeAPI)
from flowback.user.services import (user_schedule_event_create,
                                    user_schedule_event_update,
                                    user_schedule_event_delete,
                                    user_schedule_unsubscribe)
from flowback.user.selectors import user_schedule_event_list


class UserScheduleEventListAPI(ScheduleEventListTemplateAPI):
    def get(self, request):
        serializer = self.InputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        events = user_schedule_event_list(fetched_by=request.user, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=events,
                                      request=request,
                                      view=self)


class UserScheduleEventCreateAPI(ScheduleEventCreateTemplateAPI):
    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = user_schedule_event_create(user_id=request.user.id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=self.OutputSerializer(event).data)


class UserScheduleEventUpdateAPI(ScheduleEventUpdateTemplateAPI):
    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_schedule_event_update(user_id=request.user.id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class UserScheduleEventDeleteAPI(ScheduleEventDeleteAPI):
    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_schedule_event_delete(user_id=request.user.id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class UserScheduleUnsubscribeAPI(ScheduleUnsubscribeAPI):
    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_schedule_unsubscribe(user_id=request.user.id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)
