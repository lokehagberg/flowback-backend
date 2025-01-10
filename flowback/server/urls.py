from django.urls import path

from flowback.server.views import ServerConfigListAPI

server_patterns = [path('config', ServerConfigListAPI.as_view(), name='server_config'),]
