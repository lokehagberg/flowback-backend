from django.urls import path

from backend.settings import URL_SUBPATH
from .consumers import GroupChatConsumer, DirectChatConsumer, ChatConsumer
from .views import GroupMessageListApi, GroupMessagePreviewApi, DirectMessageListApi, DirectMessagePreviewApi, \
                   DirectMessageTimestampApi, GroupMessageTimestampApi

subpath = f'{URL_SUBPATH}/' if URL_SUBPATH else ''

chat_patterns = [
    path('group/<int:group>', GroupMessageListApi.as_view(), name='chat-group-list'),
    path('group/preview', GroupMessagePreviewApi.as_view(), name='chat-group-preview'),
    path('group/<int:group>/timestamp', GroupMessageTimestampApi.as_view(), name='chat-group-timestamp'),
    path('direct/<int:target>', DirectMessageListApi.as_view(), name='chat-dm-list'),
    path('direct/preview', DirectMessagePreviewApi.as_view(), name='chat-dm-preview'),
    path('direct/<int:target>/timestamp', DirectMessageTimestampApi.as_view(), name='chat-dm-timestamp'),
]

chat_ws_patterns = [
    path(subpath + 'chat/ws/group/<int:group>', GroupChatConsumer.as_asgi(), name='ws_chat_group'),
    path(subpath + 'chat/ws', ChatConsumer.as_asgi(), name='ws_chat'),
    path(subpath + 'chat/ws/direct', DirectChatConsumer.as_asgi(), name='ws_chat_direct')
]
