# Generated by Django 4.2.16 on 2025-01-24 15:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0041_grouppermissions_send_group_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='blockchain_id',
            field=models.PositiveIntegerField(blank=True, help_text='User-Defined Blockchain ID', null=True),
        ),
    ]
