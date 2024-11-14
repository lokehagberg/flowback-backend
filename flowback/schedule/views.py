from rest_framework import serializers
from rest_framework.views import APIView
from flowback.common.pagination import LimitOffsetPagination
from flowback.group.serializers import WorkGroupSerializer, GroupUserSerializer


class ScheduleEventListTemplateAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 500

    class InputSerializer(serializers.Serializer):
        start_date = serializers.DateTimeField(required=False)
        start_date__lt = serializers.DateTimeField(required=False)
        start_date__gt = serializers.DateTimeField(required=False)

        end_date = serializers.DateTimeField(required=False)
        end_date__lt = serializers.DateTimeField(required=False)
        end_date__gt = serializers.DateTimeField(required=False)

        origin_name = serializers.CharField(required=False)
        origin_id = serializers.IntegerField(required=False)

        assignee_ids = serializers.ListField(child=serializers.IntegerField(),
                                             required=False,
                                             help_text="A list of group user IDs")
        work_group_ids = serializers.CharField(required=False)

    class OutputSerializer(serializers.Serializer):
        schedule_id = serializers.IntegerField()
        event_id = serializers.IntegerField(source='id')
        title = serializers.CharField()
        description = serializers.CharField(required=False)
        start_date = serializers.DateTimeField()
        end_date = serializers.DateTimeField(required=False)
        origin_name = serializers.CharField()
        origin_id = serializers.IntegerField()
        schedule_origin_name = serializers.CharField(source='schedule.origin_name')
        schedule_origin_id = serializers.CharField(source='schedule.origin_id')
        work_group = WorkGroupSerializer(allow_null=True)
        assignees = GroupUserSerializer(many=True,
                                        allow_null=True,
                                        help_text="A list of Group Users")


class ScheduleEventCreateTemplateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        title = serializers.CharField()
        description = serializers.CharField(required=False)

        start_date = serializers.DateTimeField()
        end_date = serializers.DateTimeField(required=False)
        work_group_id = serializers.IntegerField(required=False)
        assignee_ids = serializers.ListField(child=serializers.IntegerField(),
                                             required=False,
                                             help_text="List of group user IDs (Only available for group schedules)")

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()


class ScheduleEventUpdateTemplateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        event_id = serializers.IntegerField()
        title = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        start_date = serializers.DateTimeField(required=False)
        end_date = serializers.DateTimeField(required=False)
        assignee_ids = serializers.ListField(child=serializers.IntegerField(),
                                             required=False,
                                             help_text="List of group user IDs (Only available for group schedules)")


class ScheduleEventDeleteAPI(APIView):
    class InputSerializer(serializers.Serializer):
        event_id = serializers.IntegerField()


class ScheduleUnsubscribeAPI(APIView):
    class InputSerializer(serializers.Serializer):
        target_type = serializers.CharField()
        target_id = serializers.IntegerField()
