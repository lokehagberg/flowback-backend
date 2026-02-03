from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework import status
from flowback.group.services.kanban import group_kanban_entry_create, group_kanban_entry_update, group_kanban_entry_delete

from flowback.kanban.views import KanbanEntryCreateAPI, KanbanEntryUpdateAPI, KanbanEntryDeleteAPI


@extend_schema(tags=['group/kanban'])
class GroupKanbanEntryCreateAPI(KanbanEntryCreateAPI):
    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kanban = group_kanban_entry_create(group_id=group_id,
                                           fetched_by_id=request.user.id,
                                           **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=kanban.id)


@extend_schema(tags=['group/kanban'])
class GroupKanbanEntryUpdateAPI(KanbanEntryUpdateAPI):
    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_kanban_entry_update(group_id=group_id,
                                  fetched_by_id=request.user.id,
                                  entry_id=serializer.validated_data.pop('entry_id'),
                                  data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/kanban'])
class GroupKanbanEntryDeleteAPI(KanbanEntryDeleteAPI):
    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_kanban_entry_delete(group_id=group_id, fetched_by_id=request.user.id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)
