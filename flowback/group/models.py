import uuid

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save, post_delete

from backend.settings import FLOWBACK_DEFAULT_GROUP_JOIN
from flowback.comment.models import CommentSection
from flowback.comment.services import comment_section_create
from flowback.common.models import BaseModel
from flowback.common.services import get_object
from flowback.kanban.models import Kanban
from flowback.kanban.services import kanban_create, kanban_subscription_create, kanban_subscription_delete
from flowback.schedule.models import Schedule
from flowback.schedule.services import create_schedule
from flowback.user.models import User
from django.db import models


# Create your models here.
class GroupFolder(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f'{self.id} - {self.name}'


class Group(BaseModel):
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)

    # Direct join determines if join requests requires moderation or not.
    direct_join = models.BooleanField(default=True)

    # Public determines if the group is open to public or not
    public = models.BooleanField(default=False)

    # Determines the default permission for every user get when they join
    # TODO return basic permissions by default if field is NULL
    default_permission = models.OneToOneField('GroupPermissions',
                                              null=True,
                                              blank=True,
                                              on_delete=models.SET_NULL)

    name = models.TextField(unique=True)
    description = models.TextField()
    image = models.ImageField(upload_to='group/image', null=True, blank=True)
    cover_image = models.ImageField(upload_to='group/cover_image', null=True, blank=True)
    hide_poll_users = models.BooleanField(default=False)  # Hides users in polls, TODO remove bool from views
    default_quorum = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    schedule = models.ForeignKey(Schedule, null=True, blank=True, on_delete=models.SET_NULL)
    kanban = models.ForeignKey(Kanban, null=True, blank=True, on_delete=models.SET_NULL)
    group_folder = models.ForeignKey(GroupFolder, null=True, blank=True, on_delete=models.SET_NULL)

    jitsi_room = models.UUIDField(unique=True, default=uuid.uuid4)

    @classmethod
    def post_save(cls, instance, created, update_fields, *args, **kwargs):
        if created:
            instance.schedule = create_schedule(name=instance.name, origin_name='group', origin_id=instance.id)
            instance.kanban = kanban_create(name=instance.name, origin_type='group', origin_id=instance.id)
            instance.save()
            return

        if update_fields:
            if not all(isinstance(field, str) for field in update_fields):
                update_fields = [field.name for field in update_fields]

            if 'name' in update_fields:
                instance.schedule.name = instance.name
                instance.kanban.name = instance.name
                instance.schedule.save()
                instance.kanban.save()

    @classmethod
    def user_post_save(cls, instance: User, created: bool, *args, **kwargs):
        if created and FLOWBACK_DEFAULT_GROUP_JOIN:
            for group_id in FLOWBACK_DEFAULT_GROUP_JOIN:
                if get_object(Group, id=group_id, raise_exception=False):
                    group_user = GroupUser(user=instance, group_id=group_id)
                    group_user.full_clean()
                    group_user.save()

    @classmethod
    def post_delete(cls, instance, *args, **kwargs):
        instance.schedule.delete()
        instance.kanban.delete()


post_save.connect(Group.post_save, sender=Group)
post_save.connect(Group.user_post_save, sender=User)
post_delete.connect(Group.post_delete, sender=Group)


# Permission class for each Group
class GroupPermissions(BaseModel):
    role_name = models.TextField()
    author = models.ForeignKey('Group', on_delete=models.CASCADE)
    invite_user = models.BooleanField(default=False)
    create_poll = models.BooleanField(default=True)
    poll_quorum = models.BooleanField(default=False)
    allow_vote = models.BooleanField(default=True)
    kick_members = models.BooleanField(default=False)
    ban_members = models.BooleanField(default=False)
    create_proposal = models.BooleanField(default=True)
    update_proposal = models.BooleanField(default=True)
    delete_proposal = models.BooleanField(default=True)
    force_delete_poll = models.BooleanField(default=False)
    force_delete_proposal = models.BooleanField(default=False)
    force_delete_comment = models.BooleanField(default=False)


# Permission Tags for each group, and for user to put on delegators
class GroupTags(BaseModel):
    name = models.TextField()
    group = models.ForeignKey('Group', on_delete=models.CASCADE)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('name', 'group')


# User information for the specific group
class GroupUser(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    permission = models.ForeignKey(GroupPermissions, null=True, blank=True, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)

    @classmethod
    # Updates Schedule name
    def post_save(cls, instance, created, update_fields, *args, **kwargs):
        if created:
            kanban_subscription_create(kanban_id=instance.user.kanban_id,
                                       target_id=instance.group.kanban_id)
            instance.save()
            return

    @classmethod
    def post_delete(cls, instance, *args, **kwargs):
        kanban_subscription_delete(kanban_id=instance.user.kanban_id,
                                   target_id=instance.group.kanban_id)

    class Meta:
        unique_together = ('user', 'group')


post_save.connect(GroupUser.post_save, sender=GroupUser)
post_delete.connect(GroupUser.post_delete, sender=GroupUser)


class GroupThread(BaseModel):
    created_by = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    pinned = models.BooleanField(default=False)
    comment_section = models.ForeignKey(CommentSection, default=comment_section_create, on_delete=models.DO_NOTHING)
    active = models.BooleanField(default=True)


# User invites
class GroupUserInvite(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    external = models.BooleanField()

    class Meta:
        unique_together = ('user', 'group')


class GroupUserDelegatePool(BaseModel):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)


class GroupUserDelegate(BaseModel):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    group_user = models.ForeignKey(GroupUser, on_delete=models.CASCADE)
    pool = models.ForeignKey(GroupUserDelegatePool, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('group_user', 'group')


# Delegator to delegate relations
class GroupUserDelegator(BaseModel):
    delegator = models.ForeignKey(GroupUser, on_delete=models.CASCADE, related_name='group_user_delegate_delegator')
    delegate_pool = models.ForeignKey(GroupUserDelegatePool, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    tags = models.ManyToManyField(GroupTags)

    class Meta:
        unique_together = ('delegator', 'delegate_pool', 'group')
