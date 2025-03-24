from rest_framework.test import APITransactionTestCase, APIRequestFactory, force_authenticate
from .factories import GroupFactory, GroupUserFactory, WorkGroupFactory
from ..models import GroupUser
from ..views.kanban import GroupKanbanEntryListAPI
from ...common.tests import generate_request
from ...kanban.tests.factories import KanbanEntryFactory


class TestKanban(APITransactionTestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.user = self.group.created_by
        self.group_user = GroupUser.objects.get(user=self.user, group=self.group)

        kanban_entries = [KanbanEntryFactory(kanban=self.group.kanban, created_by=self.user) for i in range(10)]

    def test_kanban_entry_list(self):
        work_group = WorkGroupFactory()
        entries = KanbanEntryFactory.create_batch(size=10, kanban=self.group.kanban, work_group=work_group)

        response = generate_request(api=GroupKanbanEntryListAPI,
                                    user=self.user,
                                    data=dict(work_group_ids=str(work_group.id)),
                                    url_params=dict(group_id=self.group.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], len(entries))
