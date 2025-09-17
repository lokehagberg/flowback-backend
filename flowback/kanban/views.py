from django.shortcuts import render

# Create your views here.
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers, status

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.kanban.models import KanbanEntry
from flowback.kanban.selectors import kanban_list
from flowback.kanban.services import kanban_entry_create, kanban_entry_update, kanban_entry_delete


class KanbanEntryListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 50
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        group_id = serializers.IntegerField(required=False)
        title__icontains = serializers.CharField(required=False)
        description__icontains = serializers.CharField(required=False)
        tag = serializers.ChoiceField((1, 2, 3, 4, 5), required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class UserSerializer(serializers.Serializer):
            id = serializers.IntegerField(source='user.id')
            profile_image = serializers.ImageField(source='user.profile_image')
            username = serializers.CharField(source='user.username')

        assignee = UserSerializer(read_only=True)
        created_by = UserSerializer(read_only=True)

        class Meta:
            model = KanbanEntry
            fields = ('id', 'created_by', 'assignee', 'title', 'description', 'tag')

    def get(self, request, group_id: int = None):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        kanban_entries = kanban_list(fetched_by=request.user, group_id=group_id, filters=serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=kanban_entries,
            request=request,
            view=self
        )


class KanbanEntryCreateAPI(APIView):
    class InputSerializer(serializers.ModelSerializer):
        assignee = serializers.CharField(source='assignee_id')

        class Meta:
            model = KanbanEntry
            fields = ('assignee', 'title', 'description', 'tag')

    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kanban = kanban_entry_create(user_id=request.user.id, group_id=group_id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=kanban.id)


class KanbanEntryUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        assignee = serializers.IntegerField(required=False, source='assignee_id')
        title = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        tag = serializers.ChoiceField((1, 2, 3, 4, 5), required=False)

    def post(self, request, group_id: int, kanban_entry_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kanban_entry_update(fetched_by=request.user.id,
                            group_id=group_id,
                            kanban_entry_id=kanban_entry_id,
                            data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class KanbanEntryDeleteAPI(APIView):
    def post(self, request, group_id: int, kanban_entry_id: int):
        kanban_entry_delete(fetched_by=request.user, group_id=group_id, kanban_entry_id=kanban_entry_id)
        return Response(status=status.HTTP_200_OK)
