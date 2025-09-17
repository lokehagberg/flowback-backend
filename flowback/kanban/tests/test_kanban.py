from django.utils import timezone
from rest_framework.test import APITestCase

from flowback.kanban.models import KanbanEntry
from flowback.kanban.services import kanban_entry_create
from flowback.kanban.tests.factories import KanbanFactory
from flowback.user.tests.factories import UserFactory


class TestKanban(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user_assignee_one, self.user_assignee_two = UserFactory.create_batch(size=2)
        self.kanban = KanbanFactory()

    def test_kanban_entry_create(self):
        entry = kanban_entry_create(kanban_id=self.kanban.id,
                                    created_by_id=self.user.id,
                                    title="Test",
                                    description="Test",
                                    lane=1,
                                    priority=1,
                                    assignee_id=self.user_assignee_one.id,
                                    end_date=timezone.now())

        self.assertTrue(KanbanEntry.objects.filter(id=entry.id).exists())
