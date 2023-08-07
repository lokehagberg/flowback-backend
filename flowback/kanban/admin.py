from django.contrib import admin
from .models import Kanban, KanbanEntry, KanbanSubscription

@admin.register(Kanban)
class KanbanAdmin(admin.ModelAdmin):
    list_display = ('name', 'origin_type', 'origin_id')

@admin.register(KanbanEntry)
class KanbanEntryAdmin(admin.ModelAdmin):
    list_display = ('kanban',
                    'created_by',
                    'assignee',
                    'end_date',
                    'priority',
                    'title',
                    'description',
                    'tag')

@admin.register(KanbanSubscription)
class KanbanSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('kanban', 'target')