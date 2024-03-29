# Generated by Django 4.0.8 on 2023-01-25 14:43
from django.db import migrations, models
import django.db.models.deletion


def pre_populate_fields(apps, schema_editor):
    Poll = apps.get_model('poll', 'poll')
    CommentSection = apps.get_model('comment', 'commentsection')
    CommentSection.objects.bulk_create([CommentSection()] * Poll.objects.all().count())
    polls = []
    for i, poll in enumerate(Poll.objects.all()):
        poll.comment_section_id = i + 1
        polls.append(poll)

    Poll.objects.bulk_update(polls, ['comment_section'])


class Migration(migrations.Migration):
    dependencies = [
        ('comment', '0001_initial'),
        ('poll', '0004_remove_poll_proposalenddategreaterthanstartdate_check_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='poll',
            name='comment_section',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='comment.commentsection'),
            preserve_default=False,
        ),
        migrations.RunPython(pre_populate_fields),
        migrations.AlterField(
            model_name='poll',
            name='comment_section',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='comment.commentsection')
        )
    ]
