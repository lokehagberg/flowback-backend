from django.contrib import admin
from .models import Notification, NotificationChannel, NotificationObject, NotificationSubscription


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(NotificationObject)
class NotificationObjectAdmin(admin.ModelAdmin):
    list_display = ('action', 'message', 'tag', 'data', 'timestamp', 'channel')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_object', 'read')


@admin.register(NotificationSubscription)
class NotificationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel')