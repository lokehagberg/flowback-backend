from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APITransactionTestCase

from flowback.group.models import GroupUser
from flowback.group.selectors import group_user_permissions
from flowback.group.tests.factories import GroupFactory, GroupUserFactory


class GroupPermissionTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.group = GroupFactory()
        self.group_creator = GroupUser.objects.get(user=self.group.created_by, group=self.group)
        self.group_user = GroupUserFactory(group=self.group)

    def test_group_permission(self):
        # Test regular permission
        self.assertEqual(group_user_permissions(user=self.group_user.user, group=self.group).id,
                         self.group_user.id)

        # Test regular user attempts admin access
        with self.assertRaises(PermissionDenied):
            group_user_permissions(user=self.group_user.user, group=self.group, permissions='admin')

        # Test group creator access admin privileges
        self.assertEqual(group_user_permissions(user=self.group_creator.user, group=self.group, permissions='admin').id,
                         self.group_creator.id)

        # Test group creator access creator privileges
        self.assertEqual(group_user_permissions(user=self.group_creator.user,
                                                group=self.group,
                                                permissions='creator').id,
                         self.group_creator.id)