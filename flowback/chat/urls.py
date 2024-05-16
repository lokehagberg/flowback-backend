from django.urls import path

from backend.settings import URL_SUBPATH
from .consumers import ChatConsumer
from .views import (MessageListAPI,
                    MessageChannelPreviewAPI,
                    MessageFileCollectionUploadAPI,
                    MessageChannelUserDataUpdateAPI,
                    MessageChannelTopicListAPI,
                    GetAllParentsOfCommentAPI,
                    GetAllChildsOfCommentAPI)

subpath = f'{URL_SUBPATH}/' if URL_SUBPATH else ''

chat_patterns = [
    path('message/channel/<int:channel_id>/list', MessageListAPI.as_view(), name='message_list'),
    path('message/channel/preview/list', MessageChannelPreviewAPI.as_view(), name='message_channel_preview'),
    path('message/channel/<int:channel_id>/file/upload', MessageFileCollectionUploadAPI.as_view(),
         name='message_channel_file_upload'),
    path('message/channel/userdata/update', MessageChannelUserDataUpdateAPI.as_view(),
         name='message_channel_userdata_update'),
    path('message/channel/<int:channel_id>/topic/list', MessageChannelTopicListAPI.as_view(),
         name='message_channel_topic_list'),
     path('message/channel/all/parent/', GetAllParentsOfCommentAPI.as_view(),
         name='message_channel_parents_of_comment'),
     path('message/channel/all/child/', GetAllChildsOfCommentAPI.as_view(),
         name='message_channel_childs_of_comment')
]

chat_ws_patterns = [
    path(subpath + 'chat/ws', ChatConsumer.as_asgi(), name='ws_chat'),
]