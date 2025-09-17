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
    image = models.ImageField()
    cover_image = models.ImageField()

    jitsi_room = models.TextField(unique=True)


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
    is_delegate = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    permission = models.ForeignKey(GroupPermissions, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('user', 'group')


# User invites
class GroupUserInvite(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    external = models.BooleanField()


# Delegator to delegate relations
class GroupUserDelegate(BaseModel):
    delegator = models.ForeignKey(GroupUser, on_delete=models.CASCADE, related_name='group_user_delegate_delegator')
    delegate = models.ForeignKey(GroupUser, on_delete=models.CASCADE, related_name='group_user_delegate_delegate')
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    tags = models.ManyToManyField(GroupTags)
