from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.group.serializers import GroupUserSerializer
from flowback.schedule.selectors import schedule_list, schedule_event_list


class ScheduleListAPI(APIView):
    lazy_action = schedule_list

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        id__in = serializers.ListField(child=serializers.IntegerField(), required=False)
        origin_name = serializers.CharField(required=False)
        origin_id = serializers.IntegerField(required=False)
        order_by = serializers.ChoiceField(choices=('created_at_asc',
                                                    'created_at_desc',
                                                    'origin_name_asc',
                                                    'origin_name_desc'),
                                           required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        origin_name = serializers.CharField(source='content_type.model')
        origin_id = serializers.IntegerField(source='object_id')

        default_tag_name = serializers.CharField(source='default_tag.name')
        default_tag_id = serializers.IntegerField(source='default_tag.id')
        available_tags = serializers.ListField(child=serializers.CharField(), allow_null=True)

    def get(self, request, *args, **kwargs):
        serializer = self.FilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = self.lazy_action.__func__(user=request.user, *args, **kwargs, filters=serializer.validated_data)

        serializer = self.OutputSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)


class ScheduleEventListAPI(APIView):
    lazy_action = schedule_event_list

    class FilterSerializer(serializers.Serializer):
        ids = serializers.CharField(required=False)
        schedule_origin_name = serializers.CharField(required=False)
        schedule_origin_id = serializers.IntegerField(required=False, help_text='Comma-separated list')
        origin_name = serializers.CharField(required=False)
        origin_ids = serializers.CharField(required=False, help_text='Comma-separated list')
        schedule_ids = serializers.CharField(required=False, help_text='Comma-separated list')
        title = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        active = serializers.BooleanField(required=False)
        tag_ids = serializers.CharField(required=False, help_text='Comma-separated list')
        assignee_user_ids = serializers.CharField(required=False, help_text='Comma-separated list')
        repeat_frequency__isnull = serializers.BooleanField(required=False)
        user_tags = serializers.CharField(required=False)
        subscribed = serializers.BooleanField(required=False)
        locked = serializers.BooleanField(required=False)

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
        serializer = self.FilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = self.lazy_action.__func__(user=request.user, *args, **kwargs, filters=serializer.validated_data)

        serializer = self.OutputSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)
