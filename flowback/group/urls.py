from django.urls import path

from .views.group import GroupListApi, GroupDetailApi, GroupCreateApi, GroupUpdateApi, GroupDeleteApi, GroupMailApi
from .views.user import (GroupUserListApi,
                         GroupUserUpdateApi,
                         GroupJoinApi,
                         GroupLeaveApi,
                         GroupInviteApi,
                         GroupInviteAcceptApi,
                         GroupInviteRejectApi)
from .views.permission import (GroupPermissionListApi,
                               GroupPermissionCreateApi,
                               GroupPermissionUpdateApi,
                               GroupPermissionDeleteApi)
from .views.tag import (GroupTagsListApi,
                        GroupTagsCreateApi,
                        GroupTagsUpdateApi,
                        GroupTagsDeleteApi)
from .views.delegate import (GroupUserDelegateListApi,
                             GroupUserDelegateApi,
                             GroupUserDelegateUpdateApi,
                             GroupUserDelegateDeleteApi,
                             GroupUserDelegatePoolListApi,
                             GroupUserDelegatePoolCreateApi,
                             GroupUserDelegatePoolDeleteApi)

group_patterns = [
    path('list', GroupListApi.as_view(), name='groups'),
    path('<int:group>/detail', GroupDetailApi.as_view(), name='group'),
    path('create', GroupCreateApi.as_view(), name='group_create'),
    path('<int:group>/update', GroupUpdateApi.as_view(), name='group_update'),
    path('<int:group>/delete', GroupDeleteApi.as_view(), name='group_delete'),
    path('<int:group>/mail', GroupMailApi.as_view(), name='group_mail'),

    path('<int:group>/users', GroupUserListApi.as_view(), name='group_users'),
    path('<int:group>/user/update', GroupUserUpdateApi.as_view(), name='group_user_update'),
    path('<int:group>/join', GroupJoinApi.as_view(), name='group_join'),
    path('<int:group>/leave', GroupLeaveApi.as_view(), name='group_leave'),
    path('<int:group>/invite', GroupInviteApi.as_view(), name='group_invite'),
    path('<int:group>/invite/accept', GroupInviteAcceptApi.as_view(), name='group_invite_accept'),
    path('<int:group>/invite/reject', GroupInviteRejectApi.as_view(), name='group_invite_reject'),

    path('<int:group>/permissions', GroupPermissionListApi.as_view(), name='group_permissions'),
    path('<int:group>/permission/create', GroupPermissionCreateApi.as_view(), name='group_permission_create'),
    path('<int:group>/permission/update', GroupPermissionUpdateApi.as_view(), name='group_permission_update'),
    path('<int:group>/permission/delete', GroupPermissionDeleteApi.as_view(), name='group_permission_delete'),

    path('<int:group>/tags', GroupTagsListApi.as_view(), name='group_tags'),
    path('<int:group>/tag/create', GroupTagsCreateApi.as_view(), name='group_tags_create'),
    path('<int:group>/tag/update', GroupTagsUpdateApi.as_view(), name='group_tags_update'),
    path('<int:group>/tag/delete', GroupTagsDeleteApi.as_view(), name='group_tags_delete'),

    path('<int:group>/delegates', GroupUserDelegateListApi.as_view(), name='group_user_delegates'),
    path('<int:group>/delegate/create', GroupUserDelegateApi.as_view(), name='group_user_delegate'),
    path('<int:group>/delegate/update', GroupUserDelegateUpdateApi.as_view(), name='group_user_delegate_update'),
    path('<int:group>/delegate/delete', GroupUserDelegateDeleteApi.as_view(), name='group_user_delegate_delete'),
    path('<int:group>/delegate/pools', GroupUserDelegatePoolListApi.as_view(), name='group_user_delegate_pools'),
    path('<int:group>/delegate/pool/create',
         GroupUserDelegatePoolCreateApi.as_view(),
         name='group_user_delegate_pool_create'),
    path('<int:group>/delegate/pool/delete',
         GroupUserDelegatePoolDeleteApi.as_view(),
         name='group_user_delegate_pool_delete'),
]
