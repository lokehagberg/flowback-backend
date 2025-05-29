from django.urls import path
from rest_framework.authtoken import views

from backend.settings import FLOWBACK_DISABLE_DEFAULT_USER_REGISTRATION
from flowback.user.views.report import ReportCreateAPI
from flowback.user.views.user import (UserCreateApi,
                                      UserCreateVerifyApi,
                                      UserListApi,
                                      UserGetApi,
                                      UserUpdateApi,
                                      UserDeleteAPI,
                                      UserForgotPasswordApi,
                                      UserForgotPasswordVerifyApi, UserGetChatChannelAPI, UserChatInviteListAPI,
                                      UserChatInviteAPI, UserLogoutAPI, UserLeaveChatChannelAPI,
                                      UserChatChannelUpdateAPI, UserNotificationSubscribeAPI)
from flowback.user.views.schedule import (UserScheduleEventListAPI,
                                          UserScheduleEventCreateAPI,
                                          UserScheduleEventUpdateAPI,
                                          UserScheduleEventDeleteAPI, UserScheduleUnsubscribeAPI)
from flowback.user.views.kanban import (UserKanbanEntryListAPI,
                                        UserKanbanEntryCreateAPI,
                                        UserKanbanEntryUpdateAPI,
                                        UserKanbanEntryDeleteAPI)
from flowback.user.views.home import UserHomeFeedAPI

user_patterns = [
    path('login', views.obtain_auth_token, name='login'),
    path('logout', UserLogoutAPI.as_view(), name='logout'),
    path('forgot_password', UserForgotPasswordApi.as_view(), name='forgot_password'),
    path('forgot_password/verify', UserForgotPasswordVerifyApi.as_view(), name='forgot_password_verify'),
    path('users', UserListApi.as_view(), name='users'),
    path('user', UserGetApi.as_view(), name='user'),
    path('user/detail', UserGetApi.as_view(), name='user'),
    path('user/update', UserUpdateApi.as_view(), name='user_update'),
    path('user/delete', UserDeleteAPI.as_view(), name='user_delete'),
    path('user/notification/subscribe',
         UserNotificationSubscribeAPI.as_view(),
         name='user_notification_subscribe'),

    path('user/schedule', UserScheduleEventListAPI.as_view(), name='user_schedule'),
    path('user/schedule/create', UserScheduleEventCreateAPI.as_view(), name='user_schedule_create'),
    path('user/schedule/update', UserScheduleEventUpdateAPI.as_view(), name='user_schedule_update'),
    path('user/schedule/delete', UserScheduleEventDeleteAPI.as_view(), name='user_schedule_delete'),
    path('user/schedule/unsubscribe', UserScheduleUnsubscribeAPI.as_view(), name='user_schedule_unsubscribe'),

    path('user/kanban/entry/list', UserKanbanEntryListAPI.as_view(), name='user_kanban_entry'),
    path('user/kanban/entry/create', UserKanbanEntryCreateAPI.as_view(), name='user_kanban_entry_create'),
    path('user/kanban/entry/update', UserKanbanEntryUpdateAPI.as_view(), name='user_kanban_entry_update'),
    path('user/kanban/entry/delete', UserKanbanEntryDeleteAPI.as_view(), name='user_kanban_entry_delete'),

    path('user/home', UserHomeFeedAPI.as_view(), name='user_home_feed'),
    path('user/chat', UserGetChatChannelAPI.as_view(), name='user_get_chat_channel'),
    path('user/chat/leave', UserLeaveChatChannelAPI.as_view(), name='user_leave_chat_channel'),
    path('user/chat/invite/list', UserChatInviteListAPI.as_view(), name='user_chat_invite_list'),
    path('user/chat/invite', UserChatInviteAPI.as_view(), name='user_chat_invite'),
    path('user/chat/update', UserChatChannelUpdateAPI.as_view(), name='user_chat_channel_update'),
    path('report/create', ReportCreateAPI.as_view(), name='report_create'),
]

if not FLOWBACK_DISABLE_DEFAULT_USER_REGISTRATION:
    user_patterns += [
        path('register', UserCreateApi.as_view(), name='register'),
        path('register/verify', UserCreateVerifyApi.as_view(), name='register_verify'),
    ]
