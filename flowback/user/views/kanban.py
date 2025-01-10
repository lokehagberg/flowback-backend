from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from flowback.common.pagination import get_paginated_response
from flowback.user.selectors import user_kanban_entry_list
from flowback.user.services import user_kanban_entry_create, user_kanban_entry_update, user_kanban_entry_delete

from flowback.kanban.views import KanbanEntryListApi, KanbanEntryCreateAPI, KanbanEntryUpdateAPI, KanbanEntryDeleteAPI


@extend_schema(tags=['user/kanban'])
class UserKanbanEntryListAPI(KanbanEntryListApi):
    def get(self, request):
        serializer = self.FilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entries = user_kanban_entry_list(fetched_by=request.user, **serializer.validated_data)
        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=entries,
                                      request=request,
                                      view=self)


@extend_schema(tags=['user/kanban'])
class UserKanbanEntryCreateAPI(KanbanEntryCreateAPI):
    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kanban = user_kanban_entry_create(user_id=request.user.id, **serializer.validated_data)

        return Response(data=kanban.id, status=status.HTTP_201_CREATED)


@extend_schema(tags=['user/kanban'])
class UserKanbanEntryUpdateAPI(KanbanEntryUpdateAPI):
    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_kanban_entry_update(user_id=request.user.id,
                                 entry_id=serializer.validated_data.pop('entry_id'),
                                 data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['user/kanban'])
class UserKanbanEntryDeleteAPI(KanbanEntryDeleteAPI):
    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_kanban_entry_delete(user_id=request.user.id, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)
