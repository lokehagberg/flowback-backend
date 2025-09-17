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
    default_permission = models.OneToOneField('GroupPermission',
                                              null=True,
                                              blank=True,
                                              on_delete=models.SET_NULL)

    name = models.TextField(unique=True)
    banner_description = models.TextField()
    description = models.TextField()
    image = models.ImageField()
    cover_image = models.ImageField()

    tags = models.ManyToManyField('GroupTags')

    jitsi_room = models.TextField(unique=True)


class GroupPermission(BaseModel):
    role_name = models.TextField()
    author = models.ForeignKey('Group', on_delete=models.CASCADE)
    invite_user = models.BooleanField(default=False)
    create_poll = models.BooleanField(default=False)
    allow_vote = models.BooleanField(default=False)
    kick_members = models.BooleanField(default=False)
    ban_members = models.BooleanField(default=False)


class GroupTags(BaseModel):
    tag_name = models.TextField()


class GroupUser(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    is_delegate = models.BooleanField(default=False)
    permission = models.ForeignKey(GroupPermission, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ('user', 'group')


class GroupUserInvite(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)


class GroupUserDelegate(BaseModel):
    delegator = models.ForeignKey(GroupUser, on_delete=models.CASCADE, related_name='group_user_delegate_delegator')
    delegate = models.ForeignKey(GroupUser, on_delete=models.CASCADE, related_name='group_user_delegate_delegate')
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    tag = models.ManyToManyField(GroupTags)
