from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework import serializers

from flowback.common.pagination import LimitOffsetPagination
from flowback.files.serializers import FileSerializer
from flowback.group.serializers import WorkGroupSerializer
from flowback.kanban.models import KanbanEntry


class KanbanEntryListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        origin_type = serializers.CharField(required=False)
        origin_id = serializers.IntegerField(required=False)
        created_by = serializers.IntegerField(required=False)
        work_group_ids = serializers.CharField(required=False)
        order_by = serializers.CharField(required=False)
        assignee = serializers.IntegerField(required=False)
        title__icontains = serializers.CharField(required=False)
        description__icontains = serializers.CharField(required=False)
        priority = serializers.ChoiceField((1, 2, 3, 4, 5), required=False)
        tag = serializers.ChoiceField((1, 2, 3, 4, 5), required=False)

    class OutputSerializer(serializers.Serializer):
        class UserSerializer(serializers.Serializer):
            id = serializers.IntegerField()
            profile_image = serializers.ImageField()
            username = serializers.CharField()

        id = serializers.IntegerField()
        assignee = UserSerializer(read_only=True, required=False)
        created_by = UserSerializer(read_only=True)
        origin_type = serializers.CharField(source='kanban.origin_type')
        origin_id = serializers.IntegerField(source='kanban.origin_id')
        priority = serializers.IntegerField()
        end_date = serializers.DateTimeField(required=False)
        title = serializers.CharField()
        description = serializers.CharField(allow_null=True, allow_blank=True)
        attachments = FileSerializer(many=True, source="attachments.filesegment_set", allow_null=True)
        work_group = WorkGroupSerializer()
        tag = serializers.IntegerField()
        category = serializers.CharField(allow_null=True)


class KanbanEntryCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        assignee = serializers.IntegerField(source='assignee_id', required=False, allow_null=True)
        work_group_id = serializers.IntegerField(required=False, allow_null=True)
        title = serializers.CharField()
        end_date = serializers.DateTimeField(required=False, allow_null=True)
        attachments = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)
        description = serializers.CharField(required=False)
        priority = serializers.ChoiceField((1, 2, 3, 4, 5), default=3)
        tag = serializers.ChoiceField((1, 2, 3, 4, 5))


class KanbanEntryUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        entry_id = serializers.IntegerField()
        assignee = serializers.IntegerField(required=False, source='assignee_id')
        title = serializers.CharField(required=False)
        description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
        end_date = serializers.DateTimeField(required=False)
        priority = serializers.ChoiceField((1, 2, 3, 4, 5), required=False)
        tag = serializers.ChoiceField((1, 2, 3, 4, 5), required=False)


class KanbanEntryDeleteAPI(APIView):
    class InputSerializer(serializers.Serializer):
        entry_id = serializers.IntegerField()
