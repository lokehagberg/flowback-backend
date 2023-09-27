# Generated by Django 4.0.8 on 2023-09-25 12:24

from django.db import migrations, models
import django.db.models.expressions


def pre_populate_fields(apps, schema_editor):
    Poll = apps.get_model('poll', 'poll')
    polls = []

    for poll in Poll.objects.all():
        area_vote_end_date = poll.proposal_end_date
        proposal_end_date = poll.prediction_statement_end_date
        prediction_statement_end_date = poll.area_vote_end_date
        poll.area_vote_end_date = area_vote_end_date
        poll.proposal_end_date = proposal_end_date
        poll.prediction_statement_end_date = prediction_statement_end_date
        polls.append(poll)

    Poll.objects.bulk_update(polls, ['prediction_statement_end_date', 'area_vote_end_date', 'proposal_end_date'])


class Migration(migrations.Migration):

    dependencies = [
        ('poll', '0013_remove_poll_votestartdategreaterthanproposalenddate_check_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='poll',
            name='proposalenddategreaterthanstartdate_check',
        ),
        migrations.RemoveConstraint(
            model_name='poll',
            name='areavoteenddategreaterthanpredictionstatementenddate_check',
        ),
        migrations.RemoveConstraint(
            model_name='poll',
            name='predictionbetenddategreaterthanareavoteenddate_check',
        ),
        migrations.RunPython(pre_populate_fields),
        migrations.AddConstraint(
            model_name='poll',
            constraint=models.CheckConstraint(check=models.Q(('area_vote_end_date__gte', django.db.models.expressions.F('start_date'))), name='areavoteenddategreaterthanstartdate_check'),
        ),
        migrations.AddConstraint(
            model_name='poll',
            constraint=models.CheckConstraint(check=models.Q(('proposal_end_date__gte', django.db.models.expressions.F('area_vote_end_date'))), name='proposalenddategreaterthanareavoteenddate_check'),
        ),
        migrations.AddConstraint(
            model_name='poll',
            constraint=models.CheckConstraint(check=models.Q(('prediction_bet_end_date__gte', django.db.models.expressions.F('prediction_statement_end_date'))), name='predictionbetenddategreaterthanpredictionstatementeneddate_check'),
        ),
    ]