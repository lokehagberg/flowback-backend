from rest_framework.test import APITransactionTestCase, APIRequestFactory, force_authenticate
from .factories import GroupFactory, GroupUserFactory
from ..views.kanban import GroupKanbanEntryListAPI
from ...kanban.tests.factories import KanbanEntryFactory


class TestKanban(APITransactionTestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.user = self.group.created_by
        self.group_user = GroupUserFactory(user=self.user, group=self.group, is_admin=True)

        kanban_entries = [KanbanEntryFactory(kanban=self.group.kanban, created_by=self.user) for i in range(10)]

    def test_kanban_list(self):
        factory = APIRequestFactory()
        view = GroupKanbanEntryListAPI.as_view()

        request = factory.get('')
        force_authenticate(request, user=self.user)
        response = view(request, group_id=self.group.id)

        print(response.data)

