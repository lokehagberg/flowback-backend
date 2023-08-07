from django.contrib import admin
from .models import Notification, NotificationChannel, NotificationObject, NotificationSubscription

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_object', 'read')


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ('category', 'sender_type', 'sender_id')


@admin.register(NotificationObject)
class NotificationObjectAdmin(admin.ModelAdmin):
    list_display = ('related_id', 'action', 'message', 'timestamp', 'channel')


@admin.register(NotificationSubscription)
class NotificationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel')