from django.test import TestCase
from rest_framework.exceptions import ValidationError

from flowback.group.models import GroupUserInvite, GroupUser
from flowback.group.services.group import group_join, group_leave
from flowback.group.services.invite import group_invite_accept, group_invite_reject
from flowback.group.tests.factories import GroupFactory, UserFactory


class TestGroupInviteFlow(TestCase):
    def setUp(self):
        """Set up test data for the invite flow test."""
        self.admin_user = UserFactory()
        self.regular_user = UserFactory()
        
        # Create a group with direct_join=False so users need to request to join
        self.group = GroupFactory(created_by=self.admin_user, public=True, direct_join=False)
        
        # GroupFactory automatically creates a GroupUser for the created_by user
        # Get the automatically created GroupUser and make sure it's an admin
        self.admin_group_user = GroupUser.objects.get(user=self.admin_user, group=self.group)
        self.admin_group_user.is_admin = True
        self.admin_group_user.save()

    def test_user_request_accept_leave_request_accept_flow(self):
        """
        Test the complete flow:
        1. User requests to join group
        2. Group admin accepts the invite
        3. User leaves the group
        4. User requests again to join the group
        5. Group admin accepts the invite again
        """
        # Step 1: User requests to join group
        # This creates a GroupUserInvite with external=True
        invite_request = group_join(user=self.regular_user.id, group=self.group.id)
        
        # Verify the request was created correctly
        self.assertIsInstance(invite_request, GroupUserInvite)
        self.assertEqual(invite_request.user, self.regular_user)
        self.assertEqual(invite_request.group, self.group)
        self.assertTrue(invite_request.external)
        
        # Verify user is not yet a group member
        self.assertFalse(GroupUser.objects.filter(
            user=self.regular_user, 
            group=self.group, 
            active=True
        ).exists())
        
        # Step 2: Group admin accepts the request
        group_invite_accept(
            fetched_by=self.admin_user.id,
            group=self.group.id,
            to=self.regular_user.id
        )
        
        # Verify user is now a group member
        group_user = GroupUser.objects.get(user=self.regular_user, group=self.group)
        self.assertTrue(group_user.active)
        
        # Verify the invite request was deleted
        self.assertFalse(GroupUserInvite.objects.filter(
            user=self.regular_user,
            group=self.group
        ).exists())
        
        # Step 3: User leaves the group
        group_leave(user=self.regular_user.id, group=self.group.id)
        
        # Verify user is no longer active in the group
        group_user.refresh_from_db()
        self.assertFalse(group_user.active)
        
        # Step 4: User requests to join the group again
        second_invite_request = group_join(user=self.regular_user.id, group=self.group.id)
        
        # Verify the second request was created correctly
        self.assertIsInstance(second_invite_request, GroupUserInvite)
        self.assertEqual(second_invite_request.user, self.regular_user)
        self.assertEqual(second_invite_request.group, self.group)
        self.assertTrue(second_invite_request.external)
        
        # Step 5: Group admin accepts the second request
        group_invite_accept(
            fetched_by=self.admin_user.id,
            group=self.group.id,
            to=self.regular_user.id
        )
        
        # Verify user is active in the group again
        group_user.refresh_from_db()
        self.assertTrue(group_user.active)
        
        # Verify the second invite request was deleted
        self.assertFalse(GroupUserInvite.objects.filter(
            user=self.regular_user,
            group=self.group
        ).exists())

    def test_user_request_accept_leave_request_reject_flow(self):
        """
        Test the complete flow with rejection at the end:
        1. User requests to join group
        2. Group admin accepts the invite
        3. User leaves the group
        4. User requests again to join the group
        5. Group admin rejects the join request
        """
        # Step 1: User requests to join group
        # This creates a GroupUserInvite with external=True
        invite_request = group_join(user=self.regular_user.id, group=self.group.id)
        
        # Verify the request was created correctly
        self.assertIsInstance(invite_request, GroupUserInvite)
        self.assertEqual(invite_request.user, self.regular_user)
        self.assertEqual(invite_request.group, self.group)
        self.assertTrue(invite_request.external)
        
        # Verify user is not yet a group member
        self.assertFalse(GroupUser.objects.filter(
            user=self.regular_user, 
            group=self.group, 
            active=True
        ).exists())
        
        # Step 2: Group admin accepts the request
        group_invite_accept(
            fetched_by=self.admin_user.id,
            group=self.group.id,
            to=self.regular_user.id
        )
        
        # Verify user is now a group member
        group_user = GroupUser.objects.get(user=self.regular_user, group=self.group)
        self.assertTrue(group_user.active)
        
        # Verify the invite request was deleted
        self.assertFalse(GroupUserInvite.objects.filter(
            user=self.regular_user,
            group=self.group
        ).exists())
        
        # Step 3: User leaves the group
        group_leave(user=self.regular_user.id, group=self.group.id)
        
        # Verify user is no longer active in the group
        group_user.refresh_from_db()
        self.assertFalse(group_user.active)
        
        # Step 4: User requests to join the group again
        second_invite_request = group_join(user=self.regular_user.id, group=self.group.id)
        
        # Verify the second request was created correctly
        self.assertIsInstance(second_invite_request, GroupUserInvite)
        self.assertEqual(second_invite_request.user, self.regular_user)
        self.assertEqual(second_invite_request.group, self.group)
        self.assertTrue(second_invite_request.external)
        
        # Step 5: Group admin rejects the second request
        group_invite_reject(
            fetched_by=self.admin_user.id,
            group=self.group.id,
            to=self.regular_user.id
        )
        
        # Verify user is still not active in the group
        group_user.refresh_from_db()
        self.assertFalse(group_user.active)
        
        # Verify the second invite request was deleted
        self.assertFalse(GroupUserInvite.objects.filter(
            user=self.regular_user,
            group=self.group
        ).exists())

    def test_cannot_request_when_already_active_member(self):
        """Test that active group members cannot request to join again."""
        # Make user an active group member first
        GroupUser.objects.create(user=self.regular_user, group=self.group, active=True)
        
        # Try to request to join - should raise ValidationError
        with self.assertRaises(ValidationError) as context:
            group_join(user=self.regular_user.id, group=self.group.id)
        
        self.assertIn('User already joined', str(context.exception))

    def test_cannot_request_when_pending_invite_exists(self):
        """Test that users cannot request to join when they already have a pending invite."""
        # Create initial request
        group_join(user=self.regular_user.id, group=self.group.id)
        
        # Try to request again - should raise ValidationError
        with self.assertRaises(ValidationError) as context:
            group_join(user=self.regular_user.id, group=self.group.id)
        
        self.assertIn('User already requested invite', str(context.exception))