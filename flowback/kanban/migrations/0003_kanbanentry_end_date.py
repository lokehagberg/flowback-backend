# Generated by Django 4.0.8 on 2023-04-12 17:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kanban', '0002_kanban_alter_kanbanentry_assignee_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='kanbanentry',
            name='end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
