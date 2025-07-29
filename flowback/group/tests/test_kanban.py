from rest_framework.test import APITestCase
from django.utils import timezone
from .factories import GroupFactory, WorkGroupFactory, GroupPermissionsFactory
from ..models import GroupUser
from ..views.kanban import GroupKanbanEntryListAPI, GroupKanbanEntryCreateAPI, GroupKanbanEntryUpdateAPI, \
    GroupKanbanEntryDeleteAPI
from ...common.tests import generate_request
from ...kanban.tests.factories import KanbanEntryFactory
from ...user.tests.factories import UserFactory
from ...kanban.models import KanbanEntry
from rest_framework.exceptions import PermissionDenied


class TestKanban(APITestCase):
    def setUp(self):
        self.group = GroupFactory(default_permission=GroupPermissionsFactory(update_kanban_task=False))
        self.user = self.group.created_by
        self.group_user = self.group.group_user_creator

        self.kanban_entries = [KanbanEntryFactory(kanban=self.group.kanban, created_by=self.user) for i in range(10)]

        # Create a user without permissions
        self.unprivileged_user = UserFactory()
        self.unprivileged_group_user = GroupUser.objects.create(
            user=self.unprivileged_user,
            group=self.group,
            is_admin=False
        )
        self.unprivileged_group_user.permission = GroupPermissionsFactory(create_kanban_task=False)
        self.unprivileged_group_user.save()

        # Create a work group for testing
        self.work_group = WorkGroupFactory(group=self.group)

    def test_kanban_entry_list(self):
        work_group = WorkGroupFactory()
        entries = KanbanEntryFactory.create_batch(size=10, kanban=self.group.kanban, work_group=work_group)

        response = generate_request(api=GroupKanbanEntryListAPI,
                                    user=self.user,
                                    data=dict(work_group_ids=str(work_group.id)),
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], len(entries))

    def test_kanban_entry_list_failure_unauthorized_user(self):
        # Create a user that doesn't belong to the group
        unauthorized_user = UserFactory()

        # This should raise a PermissionDenied exception
        with self.assertRaises(PermissionDenied):
            generate_request(api=GroupKanbanEntryListAPI,
                             user=unauthorized_user,
                             url_params=dict(group_id=self.group.id))

    def test_kanban_entry_create(self):
        data = {
            'title': 'Test Kanban Entry',
            'description': 'This is a test kanban entry',
            'priority': 3,
            'lane': 1,
            'work_group_id': self.work_group.id
        }

        response = generate_request(api=GroupKanbanEntryCreateAPI,
                                    user=self.user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        # Verify the entry was created
        self.assertTrue(KanbanEntry.objects.filter(title='Test Kanban Entry').exists())

    def test_kanban_entry_create_failure_invalid_data(self):
        # Missing required field 'title'
        data = {
            'description': 'This is a test kanban entry',
            'priority': 3,
            'lane': 1
        }

        # This should fail validation
        response = generate_request(api=GroupKanbanEntryCreateAPI,
                                    user=self.user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 400)

    def test_kanban_entry_create_failure_unauthorized_user(self):
        data = {
            'title': 'Test Kanban Entry',
            'description': 'This is a test kanban entry',
            'priority': 3,
            'lane': 1
        }

        # This should raise a PermissionDenied exception
        response = generate_request(api=GroupKanbanEntryCreateAPI,
                                    user=self.unprivileged_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 403)

    def test_kanban_entry_update(self):
        # Create an entry to update
        entry = KanbanEntryFactory(kanban=self.group.kanban, created_by=self.user, title="Original Title")

        data = {
            'entry_id': entry.id,
            'title': 'Updated Title'
        }

        response = generate_request(api=GroupKanbanEntryUpdateAPI,
                                    user=self.user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        # Verify the entry was updated
        updated_entry = KanbanEntry.objects.get(id=entry.id)
        self.assertEqual(updated_entry.title, 'Updated Title')

    def test_kanban_entry_update_failure_nonexistent_entry(self):
        data = {
            'entry_id': 99999,  # Non-existent ID
            'title': 'Updated Title'
        }

        # This should raise an exception
        response = generate_request(api=GroupKanbanEntryUpdateAPI,
                                    user=self.user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 404)

    def test_kanban_entry_update_failure_unauthorized_user(self):
        entry = KanbanEntryFactory(kanban=self.group.kanban, created_by=self.user)

        data = {
            'entry_id': entry.id,
            'title': 'Updated Title'
        }

        # This should raise a PermissionDenied exception
        response = generate_request(api=GroupKanbanEntryUpdateAPI,
                                    user=self.unprivileged_user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 403)

    def test_kanban_entry_delete(self):
        # Create an entry to delete
        entry = KanbanEntryFactory(kanban=self.group.kanban, created_by=self.user)

        data = {
            'entry_id': entry.id
        }

        response = generate_request(api=GroupKanbanEntryDeleteAPI,
                                    user=self.user,
                                    data=data,
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        # Verify the entry was deleted or is no longer accessible
        with self.assertRaises(Exception):
            KanbanEntry.objects.get(id=entry.id)

    def test_kanban_entry_delete_failure_nonexistent_entry(self):
        data = {
            'entry_id': 99999  # Non-existent ID
        }

        # This should raise an exception
        with self.assertRaises(Exception):
            generate_request(api=GroupKanbanEntryDeleteAPI,
                             user=self.user,
                             data=data,
                             url_params=dict(group_id=self.group.id))

    def test_kanban_entry_delete_failure_unauthorized_user(self):
        entry = KanbanEntryFactory(kanban=self.group.kanban, created_by=self.user)

        data = {
            'entry_id': entry.id
        }

        # This should raise a PermissionDenied exception
        with self.assertRaises(PermissionDenied):
            generate_request(api=GroupKanbanEntryDeleteAPI,
                             user=self.unprivileged_user,
                             data=data,
                             url_params=dict(group_id=self.group.id))
