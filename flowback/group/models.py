import uuid

from flowback.common.models import BaseModel
from flowback.user.models import User
from django.db import models


# Create your models here.
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
    image = models.ImageField(upload_to='group/image')
    cover_image = models.ImageField(upload_to='group/cover_image')
    hide_poll_users = models.BooleanField(default=False)  # Hides users in polls, TODO remove bool from views

    jitsi_room = models.UUIDField(unique=True, default=uuid.uuid4)


# Permission class for each Group
class GroupPermissions(BaseModel):
    role_name = models.TextField()
    author = models.ForeignKey('Group', on_delete=models.CASCADE)
    invite_user = models.BooleanField(default=False)
    create_poll = models.BooleanField(default=False)
    allow_vote = models.BooleanField(default=False)
    kick_members = models.BooleanField(default=False)
    ban_members = models.BooleanField(default=False)


# Permission Tags for each group, and for user to put on delegators
class GroupTags(BaseModel):
    tag_name = models.TextField()
    group = models.ForeignKey('Group', on_delete=models.CASCADE)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('tag_name', 'group')


# User information for the specific group
class GroupUser(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    permission = models.ForeignKey(GroupPermissions, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('user', 'group')


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
