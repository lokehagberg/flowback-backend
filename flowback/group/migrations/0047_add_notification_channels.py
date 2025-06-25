from django.db import migrations

def add_notification_channels(apps, schema_editor):
    NotificationChannel = apps.get_model('notification', 'NotificationChannel')
    Group = apps.get_model('group', 'Group')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    group_content_type = ContentType.objects.get_for_model(Group)

    for group in Group.objects.all():
        if NotificationChannel.objects.filter(content_type=group_content_type, object_id=group.id).exists():
            continue
        channel = NotificationChannel(content_type=group_content_type, object_id=group.id)
        channel.full_clean()
        channel.save()

        # NotificationChannel.objects.get_or_create(content_type=group)

class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0007_notificationchannel_parent'),
        ('group', '0046_alter_workgroup_chat_and_more'),
    ]

    operations = [
        migrations.RunPython(add_notification_channels)
    ]
