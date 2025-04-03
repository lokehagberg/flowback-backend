from django.contrib import admin
from .models import Group, GroupPermissions, GroupTags, GroupUser, GroupUserInvite, GroupUserDelegatePool, \
    GroupUserDelegate, GroupUserDelegator, GroupFolder, GroupThread


@admin.register(GroupFolder)
class GroupFolderAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('created_by', 'active', 'direct_join',
                    'public', 'default_permission', 'name',
                    'description', 'image', 'cover_image', 'poll_phase_minimum_space',
                    'hide_poll_users', 'schedule', 'kanban', 'jitsi_room', 'group_folder')

    exclude = ('chat', 'kanban', 'schedule')


@admin.register(GroupPermissions)
class GroupPermissionsAdmin(admin.ModelAdmin):
    list_display = ('id',
                    'role_name',
                    'invite_user',
                    'create_poll',
                    'poll_fast_forward',
                    'poll_quorum',
                    'allow_vote',
                    'allow_delegate',
                    'send_group_email',
                    'kick_members',
                    'ban_members',

                    'create_proposal',
                    'update_proposal',
                    'delete_proposal',

                    'prediction_statement_create',
                    'prediction_statement_delete',

                    'prediction_bet_create',
                    'prediction_bet_update',
                    'prediction_bet_delete',

                    'create_kanban_task',
                    'update_kanban_task',
                    'delete_kanban_task',

                    'force_delete_poll',
                    'force_delete_proposal',
                    'force_delete_comment')


@admin.register(GroupTags)
class GroupTagsAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'active')


@admin.register(GroupUser)
class GroupUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'is_admin', 'permission')


@admin.register(GroupUserInvite)
class GroupUserInviteAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'external')


@admin.register(GroupUserDelegatePool)
class GroupUserDelegatePoolAdmin(admin.ModelAdmin):
    list_display = ('group',)


@admin.register(GroupUserDelegate)
class GroupUserDelegateAdmin(admin.ModelAdmin):
    list_display = ('group', 'group_user', 'pool')


@admin.register(GroupUserDelegator)
class GroupUserDelegatorAdmin(admin.ModelAdmin):
    list_display = ('delegator', 'delegate_pool', 'group')


@admin.register(GroupThread)
class GroupThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'pinned', 'active', 'work_group')  # Fields visible in the list view
    list_filter = ('pinned', 'active', 'work_group')  # Filters for easy navigation
    search_fields = ('title', 'description', 'created_by__user__username')  # Search functionality
    ordering = ('-id',)  # Default ordering
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'created_by', 'work_group', 'attachments')
        }),
        ('Additional Information', {
            'fields': ('pinned', 'active', 'comment_section'),
        }),
    )
