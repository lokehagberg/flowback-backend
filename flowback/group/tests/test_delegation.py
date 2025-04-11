from django.test import TestCase

from flowback.common.services import get_object
from flowback.group.models import GroupUser, GroupUserDelegator
from flowback.group.services.delegate import (group_user_delegate,
                                              group_user_delegate_update,
                                              group_user_delegate_remove)
from flowback.group.services.tag import group_tag_create
from flowback.group.services.group import group_create, group_join, group_user_update
from flowback.group.tests.factories import GroupFactory, GroupUserFactory

from flowback.user.models import User


# TODO delegate(default, outside_group, non-delegate, self, twice, non_tags, twice_same_tag)
# TODO add permission checks
class GroupDelegationTests(TestCase):
    def setUp(self):
        self.group_one, self.group_two = GroupFactory.create_batch(2)
        self.group_one_user_one, self.group_one_user_two = GroupUserFactory.create_batch(2, group=self.group_one)
        