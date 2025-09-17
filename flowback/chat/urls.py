from django.urls import path

from .consumers import GroupChatConsumer, DirectChatConsumer
from .views import GroupMessageListApi, GroupMessagePreviewApi, DirectMessageListApi, DirectMessagePreviewApi

chat_patterns = [
    path('group/<int:group>', GroupMessageListApi.as_view(), name='chat-group-list'),
    path('group/preview', GroupMessagePreviewApi.as_view(), name='chat-group-preview'),
    path('direct/<int:target>', DirectMessageListApi.as_view(), name='chat-dm-list'),
    path('direct/preview', DirectMessagePreviewApi.as_view(), name='chat-dm-preview'),
    path('ws/group/<int:group>', GroupChatConsumer.as_asgi(), name='ws_chat_group'),
    path('ws/direct', DirectChatConsumer.as_asgi(), name='ws_chat_direct')
]
