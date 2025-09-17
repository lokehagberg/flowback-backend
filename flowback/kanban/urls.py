from django.urls import path

from .views import (KanbanEntryListApi,
                    KanbanEntryCreateAPI,
                    KanbanEntryUpdateAPI,
                    KanbanEntryDeleteAPI)


kanban_patterns = [
    path('', KanbanEntryListApi.as_view(), name='kanban_entry_list'),
    path('create', KanbanEntryCreateAPI.as_view(), name='kanban_entry_create'),
    path('<int:kanban_entry_id>/update', KanbanEntryUpdateAPI.as_view(), name='kanban_entry_update'),
    path('<int:kanban_entry_id>/delete', KanbanEntryDeleteAPI.as_view(), name='kanban_entry_delete')
]
