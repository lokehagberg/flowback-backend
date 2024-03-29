# Generated by Django 4.2.7 on 2023-11-14 13:27
import ntpath
import os

from django.db import migrations, models


def pre_populate_fields(apps, schema_editor):
    FileSegment = apps.get_model('files', 'filesegment')
    files = []

    for file in FileSegment.objects.all():
        file.file_name = ntpath.basename(file.file)
        files.append(file)

    FileSegment.objects.bulk_update(files, ['file_name'])


class Migration(migrations.Migration):
    dependencies = [
        ('files', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='filesegment',
            name='file_name',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.RunPython(pre_populate_fields),
        migrations.AlterField(
            model_name='filesegment',
            name='file_name',
            field=models.CharField(max_length=255)
        )
    ]
