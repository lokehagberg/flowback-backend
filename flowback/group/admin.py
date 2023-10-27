from django.contrib import admin
from .models import Group, GroupPermissions, GroupTags, GroupUser, GroupUserInvite, GroupUserDelegatePool, GroupUserDelegate, GroupUserDelegator


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('created_by', 'active', 'direct_join',
                    'public', 'default_permission', 'name',
                    'description', 'image', 'cover_image',
                    'hide_poll_users', 'schedule', 'kanban', 'jitsi_room')
    

@admin.register(GroupPermissions)
class GroupPermissionsAdmin(admin.ModelAdmin):
    list_display = ('role_name', 'author', 'invite_user',
                    'create_poll', 'allow_vote', 'kick_members',
                    'ban_members', 'force_delete_poll', 'force_delete_proposal',
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