# Generated by Django 4.2.16 on 2025-03-11 18:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0015_alter_userchatinvite_unique_together_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='direct_message',
        ),
    ]
