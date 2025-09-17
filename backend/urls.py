"""backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from backend.settings import DEBUG, MEDIA_URL, MEDIA_ROOT
from flowback.user.urls import user_patterns
from flowback.group.urls import group_patterns
from flowback.poll.urls import poll_patterns, PollListApi
from flowback.chat.urls import chat_patterns
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include((user_patterns, 'user'))),
    path('group/', include((group_patterns, 'group'))),
    path('chat/', include((chat_patterns, 'chat'))),
    path('group/<int:group>/poll/', include((poll_patterns, 'poll'))),
    path('home/polls', PollListApi.as_view(), name='home_polls')
]

if DEBUG:
    urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)

