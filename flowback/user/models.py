import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from rest_framework.authtoken.models import Token

from flowback.common.models import BaseModel
from flowback.kanban.services import kanban_create
from flowback.schedule.models import Schedule
from flowback.schedule.services import create_schedule


class CustomUserManager(BaseUserManager):
    def create_user(self, *, username, email, password):
        email = self.normalize_email(email)
        user = self.model(
            username=username,
            email=email,
            last_login=timezone.now()
        )

        user.set_password(password)
        user.full_clean()
        user.save()

        Token.objects.create(user=user)

        return user

    def create_superuser(self, *, username, email, password):
        email = self.normalize_email(email)
        user = self.model(
            username=username,
            email=email,
            last_login=timezone.now()
        )
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)

        Token.objects.create(user=user)

        return user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=120, unique=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    username = models.CharField(max_length=120, validators=[UnicodeUsernameValidator()], unique=True)
    profile_image = models.ImageField(null=True, blank=True, upload_to='user/profile_image')
    banner_image = models.ImageField(null=True, blank=True, upload_to='user/banner_image')
    email_notifications = models.BooleanField(default=False)
    dark_theme = models.BooleanField(default=False)

    bio = models.TextField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)

    schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, blank=True)
    kanban = models.ForeignKey('kanban.Kanban', on_delete=models.SET_NULL, null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()

    @classmethod
    # Updates Schedule name
    def post_save(cls, instance, created, update_fields, **kwargs):
        if created:
            instance.kanban = kanban_create(name=instance.username, origin_type='user', origin_id=instance.id)
            instance.schedule = create_schedule(name=instance.username, origin_name='user', origin_id=instance.id)
            instance.save()
            return

        if not update_fields:
            return

        fields = [str(field) for field in update_fields]
        if 'name' in fields:
            instance.schedule.name = instance.name
            instance.kanban.name = instance.name
            instance.kanban.save()
            instance.schedule.save()

    @classmethod
    def post_delete(cls, instance, **kwargs):
        instance.kanban.delete()
        instance.schedule.delete()


post_save.connect(User.post_save, sender=User)
post_delete.connect(User.post_delete, sender=User)


class OnboardUser(BaseModel):
    email = models.EmailField(max_length=120)
    username = models.CharField(max_length=120, validators=[UnicodeUsernameValidator()])
    verification_code = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_verified = models.BooleanField(default=False)


class PasswordReset(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    verification_code = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_verified = models.BooleanField(default=False)
