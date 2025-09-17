import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db.models.signals import post_save, post_delete
from django.utils import timezone
from django.utils.functional import classproperty
from django.utils.translation import gettext_lazy as _

from rest_framework.authtoken.models import Token
from flowback.chat.models import MessageChannelParticipant
from flowback.common.models import BaseModel
from flowback.kanban.models import Kanban
from flowback.notification.models import NotifiableModel, NotificationChannel
from flowback.schedule.models import Schedule


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


class User(AbstractBaseUser, PermissionsMixin, NotifiableModel):
    class PublicStatus(models.TextChoices):
        PUBLIC = 'public', _('Public')  # Everyone can see/access
        GROUP_ONLY = 'group_only', _('Group Only')  # Only users in the same group can see/access
        PRIVATE = 'private', _('Private')  # Only admins can see/access (._.?)

    email = models.EmailField(max_length=120, unique=True)

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    username = models.CharField(max_length=120, validators=[UnicodeUsernameValidator()], unique=True)
    profile_image = models.ImageField(null=True, blank=True, upload_to='user/profile_image')
    banner_image = models.ImageField(null=True, blank=True, upload_to='user/banner_image')
    email_notifications = models.BooleanField(default=False)
    dark_theme = models.BooleanField(default=False)
    user_config = models.TextField(null=True, blank=True)

    bio = models.TextField(null=True, blank=True)
    website = models.TextField(null=True, blank=True)
    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=20, null=True, blank=True)
    public_status = models.CharField(choices=PublicStatus.choices, default=PublicStatus.PRIVATE)
    chat_status = models.CharField(choices=PublicStatus.choices, default=PublicStatus.PRIVATE)

    schedule = models.ForeignKey('schedule.Schedule', on_delete=models.SET_NULL, null=True, blank=True)
    kanban = models.ForeignKey('kanban.Kanban', on_delete=models.SET_NULL, null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()

    @classproperty
    def message_channel_origin(self) -> str:
        return "user"

    NOTIFICATION_DATA_FIELDS = (('user_id', int, 'The ID of the user'),
                                ('username', str, "The user's username"))

    @property
    def notification_data(self) -> dict | None:
        return dict(user_id=self.id,
                    username=self.username)

    def notify_chat(self,
                    action: NotificationChannel.Action,
                    message: str,
                    message_channel_id,
                    message_channel_title: str
                    ):
        """
        Notifies chat users
        :param action: FIGHT!
        :param message:
        :param message_channel_id: Chat channel ID
        :param message_channel_title: Chat channel title
        :return:
        """
        params = locals()
        params.pop('self')

        return self.notification_channel.notify(**params)

    @classmethod
    # Updates Schedule name
    def post_save(cls, instance, created, update_fields, **kwargs):
        if created:
            kanban = Kanban(name=instance.username, origin_type='user', origin_id=instance.id)
            kanban.save()
            schedule = Schedule(name=instance.username, origin_name='user', origin_id=instance.id)
            schedule.save()

            instance.kanban = kanban
            instance.schedule = schedule
            instance.save()
            return

        elif not update_fields:
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
    email = models.EmailField(max_length=120, unique=True)
    verification_code = models.UUIDField(default=uuid.uuid4, editable=False)
    is_verified = models.BooleanField(default=False)



class PasswordReset(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    verification_code = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_verified = models.BooleanField(default=False)


class Report(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    group_id = models.IntegerField(null=True, blank=True)
    post_id = models.IntegerField(null=True, blank=True)
    post_type = models.CharField(max_length=50, null=True, blank=True)


class UserChatInvite(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message_channel = models.ForeignKey('chat.MessageChannel', on_delete=models.CASCADE)
    rejected = models.BooleanField(default=False, null=True, blank=True)

    @classmethod
    def post_save(cls, instance, created, *args, **kwargs):
        if created:
            MessageChannelParticipant.objects.create(user=instance.user, channel=instance.message_channel, active=False)
            return

        if not instance.rejected:
            MessageChannelParticipant.objects.update_or_create(user=instance.user, channel=instance.message_channel,
                                                               defaults=dict(active=True))

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'message_channel'], name='unique_user_invite')]


post_save.connect(UserChatInvite.post_save, sender=UserChatInvite)
