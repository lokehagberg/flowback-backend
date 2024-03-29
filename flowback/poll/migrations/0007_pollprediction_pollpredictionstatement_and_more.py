# Generated by Django 4.0.8 on 2023-03-23 16:44

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.expressions
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('group', '0011_group_kanban'),
        ('poll', '0006_alter_poll_comment_section'),
    ]

    operations = [
        migrations.CreateModel(
            name='PollPrediction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('score', models.IntegerField(validators=[django.core.validators.MaxValueValidator(5), django.core.validators.MinValueValidator(0)])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PollPredictionStatement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('description', models.TextField(max_length=2000)),
                ('end_date', models.DateTimeField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PollPredictionStatementSegment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_true', models.BooleanField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PollPredictionStatementVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('vote', models.BooleanField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveConstraint(
            model_name='poll',
            name='predictionenddategreaterthanproposalenddate_check',
        ),
        migrations.RemoveConstraint(
            model_name='poll',
            name='delegatevoteenddategreaterthanpredictionenddate_check',
        ),
        migrations.RenameField(
            model_name='poll',
            old_name='prediction_end_date',
            new_name='vote_start_date',
        ),
        migrations.AddConstraint(
            model_name='poll',
            constraint=models.CheckConstraint(check=models.Q(('vote_start_date__gte', django.db.models.expressions.F('proposal_end_date'))), name='votestartdategreaterthanproposalenddate_check'),
        ),
        migrations.AddConstraint(
            model_name='poll',
            constraint=models.CheckConstraint(check=models.Q(('delegate_vote_end_date__gte', django.db.models.expressions.F('vote_start_date'))), name='delegatevoteenddategreaterthanvotestartdate_check'),
        ),
        migrations.AddField(
            model_name='pollpredictionstatementvote',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='group.groupuser'),
        ),
        migrations.AddField(
            model_name='pollpredictionstatementvote',
            name='prediction_statement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='poll.pollpredictionstatement'),
        ),
        migrations.AddField(
            model_name='pollpredictionstatementsegment',
            name='prediction_statement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='poll.pollpredictionstatement'),
        ),
        migrations.AddField(
            model_name='pollpredictionstatementsegment',
            name='proposal',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='poll.pollproposal'),
        ),
        migrations.AddField(
            model_name='pollpredictionstatement',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='group.groupuser'),
        ),
        migrations.AddField(
            model_name='pollpredictionstatement',
            name='poll',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='poll.poll'),
        ),
        migrations.AddField(
            model_name='pollprediction',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='group.groupuser'),
        ),
        migrations.AddField(
            model_name='pollprediction',
            name='prediction_statement',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='poll.pollpredictionstatement'),
        ),
    ]
