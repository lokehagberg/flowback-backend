from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework import serializers

from flowback.common.pagination import LimitOffsetPagination
from flowback.kanban.models import KanbanEntry


class KanbanEntryListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        origin_type = serializers.CharField(required=False)
        origin_id = serializers.IntegerField(required=False)
        created_by = serializers.IntegerField(required=False)
        order_by = serializers.CharField(required=False)
        assignee = serializers.IntegerField(required=False)
        title__icontains = serializers.CharField(required=False)
        description__icontains = serializers.CharField(required=False)
        priority = serializers.ChoiceField((1, 2, 3, 4, 5), required=False)
        tag = serializers.ChoiceField((1, 2, 3, 4, 5), required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class UserSerializer(serializers.Serializer):
            id = serializers.IntegerField()
            profile_image = serializers.ImageField()
            username = serializers.CharField()

        assignee = UserSerializer(read_only=True, required=False)
        created_by = UserSerializer(read_only=True)
        origin_type = serializers.CharField(source='kanban.origin_type')
        origin_id = serializers.IntegerField(source='kanban.origin_id')
        priority = serializers.IntegerField()
        end_date = serializers.DateTimeField(required=False)

        class Meta:
            model = KanbanEntry
            fields = ('id',
                      'origin_type',
                      'origin_id',
                      'created_by',
                      'assignee',
                      'title',
                      'description',
                      'end_date',
                      'priority',
                      'tag')


class KanbanEntryCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        assignee = serializers.IntegerField(source='assignee_id', required=False, allow_null=True)
        title = serializers.CharField()
        end_date = serializers.DateTimeField(required=False, allow_null=True)
        description = serializers.CharField(required=False)
        priority = serializers.ChoiceField((1, 2, 3, 4, 5), default=3)
        tag = serializers.ChoiceField((1, 2, 3, 4, 5))


class KanbanEntryUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        entry_id = serializers.IntegerField()
        assignee = serializers.IntegerField(required=False, source='assignee_id')
        title = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        end_date = serializers.DateTimeField(required=False)
        priority = serializers.ChoiceField((1, 2, 3, 4, 5), required=False)
        tag = serializers.ChoiceField((1, 2, 3, 4, 5), required=False)


class KanbanEntryDeleteAPI(APIView):
    class InputSerializer(serializers.Serializer):
        entry_id = serializers.IntegerField()
