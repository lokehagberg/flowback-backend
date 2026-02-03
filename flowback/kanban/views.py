import math

from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework import serializers

from backend.settings import FLOWBACK_KANBAN_LANES, FLOWBACK_KANBAN_PRIORITY_LIMIT
from flowback.common.pagination import LimitOffsetPagination
from flowback.files.serializers import FileSerializer, FileCollectionCreateSerializerMixin, \
    FileCollectionUpdateSerializerMixin, FileCollectionListSerializerMixin
from flowback.group.serializers import WorkGroupSerializer
from flowback.kanban.models import KanbanEntry


class KanbanEntryListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        origin_type = serializers.CharField(required=False)
        origin_id = serializers.IntegerField(required=False)
        work_group_ids = serializers.CharField(required=False)
        created_by = serializers.IntegerField(required=False)
        order_by = serializers.CharField(required=False)
        assignee = serializers.IntegerField(required=False)
        title__icontains = serializers.CharField(required=False)
        description__icontains = serializers.CharField(required=False)
        priority = serializers.ChoiceField(range(1, FLOWBACK_KANBAN_PRIORITY_LIMIT + 1), required=False)
        lane = serializers.ChoiceField(range(1, len(FLOWBACK_KANBAN_LANES) + 1), required=False)

    class OutputSerializer(FileCollectionListSerializerMixin, serializers.Serializer):
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
        work_group = WorkGroupSerializer()
        lane = serializers.IntegerField()
        category = serializers.CharField(allow_null=True)


class KanbanEntryCreateAPI(APIView):
    class InputSerializer(FileCollectionCreateSerializerMixin, serializers.Serializer):
        assignee_id = serializers.IntegerField(required=False, allow_null=True)
        work_group_id = serializers.IntegerField(required=False, allow_null=True)
        title = serializers.CharField()
        end_date = serializers.DateTimeField(required=False, allow_null=True)
        description = serializers.CharField(required=False)
        priority = serializers.ChoiceField(range(1, FLOWBACK_KANBAN_PRIORITY_LIMIT + 1),
                                           default=math.floor(FLOWBACK_KANBAN_PRIORITY_LIMIT / 2))
        lane = serializers.ChoiceField(range(1, len(FLOWBACK_KANBAN_LANES) + 1))


class KanbanEntryUpdateAPI(APIView):
    class InputSerializer(FileCollectionUpdateSerializerMixin, serializers.Serializer):
        entry_id = serializers.IntegerField()
        work_group_id = serializers.IntegerField(required=False, allow_null=True)
        assignee_id = serializers.IntegerField(required=False)
        title = serializers.CharField(required=False)
        description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
        end_date = serializers.DateTimeField(required=False)
        priority = serializers.ChoiceField(range(1, FLOWBACK_KANBAN_PRIORITY_LIMIT + 1),
                                           required=False)
        lane = serializers.ChoiceField(range(1, len(FLOWBACK_KANBAN_LANES) + 1), required=False)


class KanbanEntryDeleteAPI(APIView):
    class InputSerializer(serializers.Serializer):
        entry_id = serializers.IntegerField()
