import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone

from rest_framework.authtoken.models import Token

from flowback.common.models import BaseModel


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
    profile_image = models.ImageField(null=True, blank=True)
    banner_image = models.ImageField(null=True, blank=True)

    bio = models.TextField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()


class OnboardUser(BaseModel):
    email = models.EmailField(max_length=120)
    username = models.CharField(max_length=120, validators=[UnicodeUsernameValidator()])
    verification_code = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_verified = models.BooleanField(default=False)


class PasswordReset(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    verification_code = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_verified = models.BooleanField(default=False)
