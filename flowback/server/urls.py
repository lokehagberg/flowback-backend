from django.urls import path

from flowback.server.views import ServerConfigListAPI, ServerReportListAPI

server_patterns = [path('config', ServerConfigListAPI.as_view(), name='server_config'),
                   path('reports', ServerReportListAPI.as_view(), name='server_reports')]
