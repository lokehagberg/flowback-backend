from django.db import migrations

def add_notification_channels(apps, schema_editor):
    NotificationChannel = apps.get_model('notification', 'NotificationChannel')
    Group = apps.get_model('group', 'Group')

    for group in Group.objects.all():
        NotificationChannel.objects.get_or_create(content_type=Group, object_id=group.id)

class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0007_notificationchannel_parent'),
        ('group', '0046_alter_workgroup_chat_and_more'),
    ]

    operations = [
        migrations.RunPython(add_notification_channels)
    ]
