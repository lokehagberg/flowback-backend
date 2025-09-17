from django.core.exceptions import ValidationError

from .models import Notification
from ..user.models import User


def notification_update(*, user: User,
                        notification_object_ids: list[Notification | int],
                        read: bool) -> None:
    notifications = Notification.objects.filter(user=user,
                                                notification_object_id__in=notification_object_ids)

    if not notifications:
        raise ValidationError('No notifications found')

    notifications.update(read=read)


## notification_delete
## notification_mark_read
## notification_channel_subscribe
## notification_channel_unsubscribe
