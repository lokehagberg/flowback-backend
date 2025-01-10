from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.common.pagination import get_paginated_response
from flowback.schedule.views import (ScheduleEventListTemplateAPI,
                                     ScheduleEventCreateTemplateAPI,
                                     ScheduleEventUpdateTemplateAPI,
                                     ScheduleEventDeleteAPI)
from flowback.group.services.schedule import (group_schedule_event_create,
                                              group_schedule_event_update,
                                              group_schedule_event_delete,
                                              group_schedule_subscribe)
from flowback.group.selectors import group_schedule_event_list


@extend_schema(tags=['group/schedule'])
class GroupScheduleEventListAPI(ScheduleEventListTemplateAPI):
    def get(self, request, group_id: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        events = group_schedule_event_list(fetched_by=request.user,
                                           group_id=group_id,
                                           filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=events,
                                      request=request,
                                      view=self)


@extend_schema(tags=['group/schedule'])
class GroupScheduleEventCreateAPI(ScheduleEventCreateTemplateAPI):
    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event = group_schedule_event_create(user_id=request.user.id, group_id=group_id, **serializer.validated_data)
        output = self.OutputSerializer(event)

        return Response(status=status.HTTP_200_OK, data=output.data)


@extend_schema(tags=['group/schedule'])
class GroupScheduleEventUpdateAPI(ScheduleEventUpdateTemplateAPI):
    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_schedule_event_update(user_id=request.user.id, group_id=group_id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/schedule'])
class GroupScheduleEventDeleteAPI(ScheduleEventDeleteAPI):
    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_schedule_event_delete(user_id=request.user.id, group_id=group_id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/schedule'])
class GroupScheduleSubscribeAPI(APIView):
    def post(self, request, group_id: int):
        group_schedule_subscribe(user_id=request.user.id, group_id=group_id)
        return Response(status=status.HTTP_200_OK)
