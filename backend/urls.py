from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularRedocView, SpectacularAPIView

from backend.settings import DEBUG, MEDIA_URL, MEDIA_ROOT, URL_SUBPATH, INTEGRATIONS
from flowback.poll.views.poll import PollUserScheduleListAPI, PollListApi
from flowback.user.urls import user_patterns
from flowback.group.urls import group_patterns
from flowback.poll.urls import group_poll_patterns, poll_patterns
from flowback.chat.urls import chat_patterns
from flowback.notification.urls import notification_patterns
from flowback.server.urls import server_patterns
from flowback.schedule.urls import schedule_patterns
from django.conf.urls.static import static


api_urlpatterns = [
    path('', include((user_patterns, 'user'))),
    path('group/', include((group_patterns, 'group'))),
    path('chat/', include((chat_patterns, 'chat'))),
    path('group/<int:group_id>/poll/', include((group_poll_patterns, 'group_poll'))),
    path('group/poll/', include((poll_patterns, 'poll'))),
    path('notification/', include((notification_patterns, 'notification'))),
    path('server/', include((server_patterns, 'server'))),
    path('schedule/', include((schedule_patterns, 'schedule'))),

    path('home/polls', PollListApi.as_view(), name='home_polls'),
    path('poll/user/schedule', PollUserScheduleListAPI.as_view(), name='poll_user_schedule'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]

if INTEGRATIONS:
    try:
        from flowback_addon.urls import addon_patterns
        api_urlpatterns.append(path('', include((addon_patterns, 'addon'))))

    except ModuleNotFoundError:
        pass

    except Exception as e:
        raise e

urlpatterns = [
    path(f'{URL_SUBPATH}/' if URL_SUBPATH else '', include((api_urlpatterns, 'api'))),
    path('admin/', admin.site.urls, name='admin'),
    path('openid/', include('oidc_provider.urls', namespace='oidc_provider')),
]

if DEBUG:
    urlpatterns += static((f'/{URL_SUBPATH}' if URL_SUBPATH else '') + MEDIA_URL,
                          document_root=MEDIA_ROOT)
