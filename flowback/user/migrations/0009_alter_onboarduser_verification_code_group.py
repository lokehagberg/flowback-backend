# Generated by Django 4.0.3 on 2022-04-28 13:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0008_alter_onboarduser_verification_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='onboarduser',
            name='verification_code',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('active', models.BooleanField(default=True)),
                ('direct_join', models.BooleanField(default=True)),
                ('public', models.BooleanField(default=False)),
                ('name', models.TextField(unique=True)),
                ('banner_description', models.TextField()),
                ('description', models.TextField()),
                ('image', models.TextField()),
                ('cover_image', models.ImageField(upload_to='')),
                ('jitsi_room', models.TextField(unique=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]