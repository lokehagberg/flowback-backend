from django.test import TestCase
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError

from flowback.common.services import get_object
from flowback.group.models import Group, GroupUser, GroupUserDelegator, GroupUserDelegate
from flowback.group.services import (group_user_delegate,
                                     group_user_delegate_update,
                                     group_user_delegate_remove,
                                     group_create,
                                     group_tag_create,
                                     group_user_update,
                                     group_join,
                                     group_leave)

from flowback.group.selectors import group_user_permissions
from flowback.user.models import User


# TODO delegate(default, outside_group, non-delegate, self, twice, non_tags, twice_same_tag)
# TODO add permission checks
class GroupDelegationTests(TestCase):
    def setUp(self):
        self.user_creator = User.objects.create_superuser(username='user_creator',
                                                          email='creator@example.com',
                                                          password='password123')
        self.user_delegate = User.objects.create_user(username='user_delegate',
                                                      email='member@example.com',
                                                      password='password123')
        self.user_delegator = User.objects.create_user(username='user_delegator',
                                                       email='member_2@example.com',
                                                       password='password123')
        self.user_non_delegate = User.objects.create_user(username='user_non_delegate',
                                                          email='member_3@example.com',
                                                          password='password123')
        self.user_non_member = User.objects.create_user(username='user_non_member',
                                                        email='member_4@example.com',
                                                        password='password123')
        self.group = group_create(user=self.user_creator.id,
                                  name='test_group',
                                  description='desc',
                                  image='image',
                                  cover_image='cover_image',
                                  public=True,
                                  direct_join=True)

        self.user_delegator = group_join(user=self.user_delegator.id, group=self.group.id)
        self.user_delegate = group_join(user=self.user_delegate.id, group=self.group.id)
        self.user_delegate = group_user_update(user=self.user_delegate.user.id,
                                               group=self.group.id,
                                               fetched_by=self.user_delegate.user.id,
                                               data=dict(delegate=True))

        self.user_non_delegate = group_join(user=self.user_non_delegate.id, group=self.group.id)
        self.user_creator = get_object(GroupUser, user=self.user_creator, group=self.group)

        self.tag_one = group_tag_create(user=self.user_creator.user.id, group=self.group.id, tag_name='tag_one')
        self.tag_two = group_tag_create(user=self.user_creator.user.id, group=self.group.id, tag_name='tag_two')
        self.tag_three = group_tag_create(user=self.user_creator.user.id, group=self.group.id, tag_name='tag_three')

    def generate_delegate(self):
        return group_user_delegate(user=self.user_delegator.user.id,
                                   delegate=self.user_delegate.groupuserdelegate.id,
                                   group=self.group.id,
                                   tags=[self.tag_one.id, self.tag_two.id])

    def test_delegate(self):
        delegate_rel = self.generate_delegate()

        self.assertEqual(delegate_rel.delegate, self.user_delegate.groupuserdelegate)
        self.assertEqual(delegate_rel.delegator, self.user_delegator)
        self.assertEqual(delegate_rel.group, self.group)
        self.assertTrue(delegate_rel.tags.filter(id=self.tag_one.id).exists())
        self.assertTrue(delegate_rel.tags.filter(id=self.tag_two.id).exists())
        self.assertFalse(delegate_rel.tags.filter(id=self.tag_three.id).exists())

    def test_delegate_update(self):
        delegate_rel = self.generate_delegate()
        delegate_rel = group_user_delegate_update(user_id=self.user_delegator.user.id,
                                                  delegate_id=delegate_rel.delegate.id,
                                                  group_id=self.group.id,
                                                  tags=[self.tag_one.id, self.tag_three.id])

        self.assertTrue(delegate_rel.tags.filter(id=self.tag_one.id).exists())
        self.assertFalse(delegate_rel.tags.filter(id=self.tag_two.id).exists())
        self.assertTrue(delegate_rel.tags.filter(id=self.tag_three.id).exists())

    def test_delegate_delete(self):
        delegate_rel = self.generate_delegate()
        target_id = delegate_rel.id
        group_user_delegate_remove(user_id=delegate_rel.delegator.user.id,
                                   group_id=delegate_rel.group.id,
                                   delegate_id=delegate_rel.delegate.id)

        self.assertFalse(GroupUserDelegator.objects.filter(id=target_id).exists())
