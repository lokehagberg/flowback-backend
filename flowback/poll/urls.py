from django.urls import path

from .views import (PollListApi,
                    PollCreateAPI,
                    PollUpdateAPI,
                    PollDeleteAPI)


poll_patterns = [
    path('list', PollListApi.as_view(), name='polls'),
    path('create', PollCreateAPI.as_view(), name='poll_create'),
    path('<int:poll>/update', PollUpdateAPI.as_view(), name='poll_update'),
    path('<int:poll>/delete', PollDeleteAPI.as_view(), name='poll_delete')
]