# Generated by Django 4.2.7 on 2024-08-14 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('poll', '0039_pollpredictionstatement_title'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pollpredictionstatement',
            name='description',
            field=models.TextField(blank=True, max_length=2000, null=True),
        ),
    ]