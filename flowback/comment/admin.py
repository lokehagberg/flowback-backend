from django.contrib import admin
from .models import Comment

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('comment_section', 'author', 'message', 'edited', 'active', 'parent', 'score', 'created_at', 'updated_at')
    list_filter = ('edited', 'active', 'score')
    search_fields = ('author__email__icontains',)
    date_hierarchy = 'created_at'
    ordering = ('-author', 'author')