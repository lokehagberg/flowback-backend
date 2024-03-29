# Generated by Django 4.0.8 on 2023-09-27 14:20

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0015_alter_group_cover_image_alter_group_image'),
        ('poll', '0014_remove_poll_proposalenddategreaterthanstartdate_check_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PollAreaStatement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='group.groupuser')),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='poll.poll')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PollAreaStatementSegment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('poll_area_statement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='poll.pollareastatement')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='group.grouptags')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PollAreaStatementVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('vote', models.BooleanField()),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='group.groupuser')),
                ('poll_area_statement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='poll.pollareastatement')),
            ],
            options={
                'unique_together': {('created_by', 'poll_area_statement')},
            },
        ),
    ]
