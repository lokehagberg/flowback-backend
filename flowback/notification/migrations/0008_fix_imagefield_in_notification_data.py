from django.db import migrations
from django.db.models.fields.files import ImageFieldFile


def update_notification_objects(apps, schema_editor):
    NotificationObject = apps.get_model('notification', 'NotificationObject')
    qs = NotificationObject.objects.exclude(data=None).only('id', 'data')

    for notification_object in qs:
        if notification_object.data:
            for k, v in notification_object.data.items():
                if isinstance(v, ImageFieldFile):
                    notification_object.data[k] = v.url
                    notification_object.save()


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0007_notificationchannel_parent'),
    ]

    operations = [
        migrations.RunPython(update_notification_objects),
    ]
