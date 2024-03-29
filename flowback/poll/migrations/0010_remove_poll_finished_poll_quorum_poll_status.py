# Generated by Django 4.0.8 on 2023-06-02 15:43

import django.core.validators
from django.db import migrations, models


def pre_populate_fields(apps, schema_editor):
    Poll = apps.get_model('poll', 'poll')
    polls = []

    for i, poll in enumerate(Poll.objects.all()):
        poll.status = int(poll.result)
        polls.append(poll)

    Poll.objects.bulk_update(polls, ['status'])


class Migration(migrations.Migration):

    dependencies = [
        ('poll', '0009_alter_poll_poll_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='poll',
            name='status',
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(pre_populate_fields),
        migrations.RemoveField(
            model_name='poll',
            name='finished',
        ),
        migrations.AddField(
            model_name='poll',
            name='quorum',
            field=models.IntegerField(blank=True, default=None, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)]),
        ),
    ]
