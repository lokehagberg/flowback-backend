from rest_framework.response import Response
from rest_framework import status, serializers

from flowback.common.pagination import get_paginated_response
from flowback.group.selectors import group_kanban_entry_list
from flowback.group.services.kanban import group_kanban_entry_create, group_kanban_entry_update, group_kanban_entry_delete

from flowback.kanban.views import KanbanEntryListApi, KanbanEntryCreateAPI, KanbanEntryUpdateAPI, KanbanEntryDeleteAPI


class GroupKanbanEntryListAPI(KanbanEntryListApi):
    class OutputSerializer(KanbanEntryListApi.OutputSerializer):
        work_group_ids = serializers.CharField(required=False)
        group_name = serializers.CharField()

    def get(self, request, group_id: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        entries = group_kanban_entry_list(fetched_by=request.user, group_id=group_id, filters=serializer.validated_data)
        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=entries,
                                      request=request,
                                      view=self)


class GroupKanbanEntryCreateAPI(KanbanEntryCreateAPI):
    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kanban = group_kanban_entry_create(group_id=group_id,
                                           fetched_by_id=request.user.id,
                                           **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=kanban.id)


class GroupKanbanEntryUpdateAPI(KanbanEntryUpdateAPI):
    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_kanban_entry_update(group_id=group_id,
                                  fetched_by_id=request.user.id,
                                  entry_id=serializer.validated_data.pop('entry_id'),
                                  data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class GroupKanbanEntryDeleteAPI(KanbanEntryDeleteAPI):
    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_kanban_entry_delete(group_id=group_id, fetched_by_id=request.user.id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)
