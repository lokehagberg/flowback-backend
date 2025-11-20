from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.common.pagination import get_paginated_response, LimitOffsetPagination
from flowback.group.serializers import GroupUserSerializer
from flowback.schedule.selectors import schedule_list, schedule_event_list
from flowback.common.fields import CharacterSeparatedField
from flowback.schedule.services import (schedule_event_subscribe,
                                        schedule_event_unsubscribe,
                                        schedule_tag_subscribe,
                                        schedule_tag_unsubscribe,
                                        schedule_subscribe_to_new_tags,
                                        schedule_unsubscribe_to_new_tags,
                                        schedule_event_create,
                                        schedule_event_update,
                                        schedule_event_delete)


class ScheduleListAPI(APIView):
    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        ids = serializers.CharField(required=False)
        origin_name = serializers.CharField(required=False)
        origin_ids = serializers.CharField(required=False)
        order_by = serializers.ChoiceField(choices=('created_at_asc',
                                                    'created_at_desc',
                                                    'origin_name_asc',
                                                    'origin_name_desc'),
                                           required=False)

    class OutputSerializer(serializers.Serializer):
        class ScheduleTagSerializer(serializers.Serializer):
            id = serializers.IntegerField()
            name = serializers.CharField()

        id = serializers.IntegerField()
        origin_name = serializers.CharField(source='content_type.model')
        origin_id = serializers.IntegerField(source='object_id')
        default_tag = ScheduleTagSerializer()

        available_tags = serializers.ListField(child=serializers.CharField(), allow_null=True)

    def get(self, request):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        schedules = schedule_list(user=request.user, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=LimitOffsetPagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=schedules,
                                      request=request,
                                      view=self)


class ScheduleEventListAPI(APIView):
    class FilterSerializer(serializers.Serializer):
        ids = serializers.CharField(required=False, help_text='comma-separated list of integers')
        schedule_origin_name = serializers.CharField(required=False)
        schedule_origin_id = serializers.CharField(required=False, help_text='comma-separated list of integers')
        origin_name = serializers.CharField(required=False)
        origin_ids = serializers.CharField(required=False, help_text='comma-separated list of integers')
        schedule_ids = serializers.CharField(required=False, help_text='comma-separated list of integers')
        title = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        active = serializers.BooleanField(required=False, allow_null=True, default=None)
        tag_ids = serializers.CharField(required=False, help_text='comma-separated list of integers')
        assignee_user_ids = serializers.CharField(required=False, help_text='comma-separated list of integers')
        repeat_frequency__isnull = serializers.BooleanField(required=False, allow_null=True, default=None)
        user_tags = serializers.CharField(required=False)
        subscribed = serializers.BooleanField(required=False, allow_null=True, default=None)
        locked = serializers.BooleanField(required=False, allow_null=True, default=None)

        # Field lookups from Meta.fields
        start_date = serializers.DateTimeField(required=False)
        start_date__lt = serializers.DateTimeField(required=False)
        start_date__gt = serializers.DateTimeField(required=False)
        end_date = serializers.DateTimeField(required=False)
        end_date__lt = serializers.DateTimeField(required=False)
        end_date__gt = serializers.DateTimeField(required=False)
        tag = serializers.CharField(required=False)
        tag__icontains = serializers.CharField(required=False)

        order_by = serializers.ChoiceField(choices=(
            'created_at_asc', 'created_at_desc',
            'start_date_asc', 'start_date_desc',
            'end_date_asc', 'end_date_desc'
        ), required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        schedule_id = serializers.IntegerField()
        title = serializers.CharField()
        description = serializers.CharField(allow_null=True)
        start_date = serializers.DateTimeField()
        end_date = serializers.DateTimeField(allow_null=True)
        active = serializers.BooleanField()
        meeting_link = serializers.CharField(allow_null=True)
        repeat_frequency = serializers.IntegerField(allow_null=True)

        tag_id = serializers.IntegerField(source='tag.id', allow_null=True)
        tag_name = serializers.CharField(source='tag.name', allow_null=True)
        origin_name = serializers.CharField(source='content_type.model')
        origin_id = serializers.IntegerField(source='object_id')
        schedule_origin_name = serializers.CharField(source='schedule.content_type.model')
        schedule_origin_id = serializers.IntegerField(source='schedule.object_id')
        assignees = GroupUserSerializer(many=True)

        reminders = serializers.ListField(child=serializers.IntegerField(), allow_null=True)
        user_tags = serializers.ListField(child=serializers.CharField(), allow_null=True)
        locked = serializers.BooleanField(allow_null=True)
        subscribed = serializers.BooleanField()

    def get(self, request, *args, **kwargs):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        events = schedule_event_list(user=request.user, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=LimitOffsetPagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=events,
                                      request=request,
                                      view=self)


class ScheduleSubscribeAPI(APIView):
    class InputSerializer(serializers.Serializer):
        reminders = CharacterSeparatedField(child=serializers.IntegerField(),
                                            required=False,
                                            allow_null=True,
                                            max_length=10)

    def post(self, request, schedule_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        schedule_subscribe_to_new_tags(user=request.user,
                                       schedule_id=schedule_id,
                                       **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class ScheduleUnsubscribeAPI(APIView):
    def post(self, request, schedule_id: int):
        schedule_unsubscribe_to_new_tags(user=request.user,
                                         schedule_id=schedule_id)
        return Response(status=status.HTTP_200_OK)


class ScheduleEventSubscribeAPI(APIView):
    class InputSerializer(serializers.Serializer):
        event_ids = CharacterSeparatedField(child=serializers.IntegerField())
        user_tags = CharacterSeparatedField(child=serializers.CharField(),
                                            required=False,
                                            allow_null=True)
        locked = serializers.BooleanField(required=False, default=True)
        reminders = CharacterSeparatedField(child=serializers.IntegerField(),
                                            required=False,
                                            allow_null=True,
                                            max_length=10)

    def post(self, request, schedule_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        schedule_event_subscribe(user=request.user,
                                 schedule_id=schedule_id,
                                 **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class ScheduleEventUnsubscribeAPI(APIView):
    class InputSerializer(serializers.Serializer):
        event_ids = CharacterSeparatedField(child=serializers.IntegerField())

    def post(self, request, schedule_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        schedule_event_unsubscribe(user=request.user,
                                   schedule_id=schedule_id,
                                   **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class ScheduleTagSubscribeAPI(APIView):
    class InputSerializer(serializers.Serializer):
        tag_ids = CharacterSeparatedField(child=serializers.IntegerField())
        reminders = CharacterSeparatedField(child=serializers.IntegerField(),
                                            required=False,
                                            allow_null=True,
                                            max_length=10)

    def post(self, request, schedule_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        schedule_tag_subscribe(user=request.user,
                               schedule_id=schedule_id,
                               **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class ScheduleTagUnsubscribeAPI(APIView):
    class InputSerializer(serializers.Serializer):
        tag_ids = CharacterSeparatedField(child=serializers.IntegerField())

    def post(self, request, schedule_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        schedule_tag_unsubscribe(user=request.user,
                                 schedule_id=schedule_id,
                                 **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class ScheduleEventLazyCreateAPI(APIView):
    lazy_action = schedule_event_create

    class InputSerializer(serializers.Serializer):
        title = serializers.CharField()
        description = serializers.CharField(allow_blank=True, required=False)
        start_date = serializers.DateTimeField()
        end_date = serializers.DateTimeField(required=False, allow_null=True)
        tag = serializers.CharField(required=False, allow_blank=True)
        assignees = CharacterSeparatedField(child=serializers.IntegerField(), required=False)
        meeting_link = serializers.CharField(required=False, allow_blank=True)
        repeat_frequency = serializers.IntegerField(required=False, allow_null=True)

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if kwargs.get('schedule_id'):
            data = kwargs.get('schedule_id')

        self.lazy_action.__func__(user=request.user, **data)

        return Response(status=status.HTTP_200_OK)


class ScheduleEventLazyUpdateAPI(APIView):
    lazy_action = schedule_event_update

    class InputSerializer(serializers.Serializer):
        event_id = serializers.IntegerField()

        title = serializers.CharField(required=False)
        description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
        start_date = serializers.DateTimeField(required=False)
        end_date = serializers.DateTimeField(required=False, allow_null=True)
        tag = serializers.CharField(required=False, allow_blank=True, allow_null=True)
        assignees = CharacterSeparatedField(child=serializers.IntegerField(), required=False)
        meeting_link = serializers.CharField(required=False, allow_blank=True, allow_null=True)
        repeat_frequency = serializers.IntegerField(required=False, allow_null=True)

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.lazy_action.__func__(user=request.user,
                                  schedule_id=kwargs.get('schedule_id'),
                                  **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class ScheduleEventLazyDeleteAPI(APIView):
    lazy_action = schedule_event_delete

    class InputSerializer(serializers.Serializer):
        event_id = serializers.IntegerField()

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.lazy_action.__func__(user=request.user,
                                  schedule_id=kwargs.get('schedule_id'),
                                  **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)
