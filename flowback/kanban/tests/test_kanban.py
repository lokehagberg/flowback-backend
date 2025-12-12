from django.utils import timezone
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from flowback.common.tests import generate_request
from flowback.kanban.models import KanbanEntry
from flowback.kanban.services import kanban_entry_create
from flowback.kanban.tests.factories import KanbanFactory, KanbanEntryFactory
from flowback.user.tests.factories import UserFactory
from flowback.user.views.kanban import UserKanbanEntryUpdateAPI


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

    def test_kanban_entry_update_with_attachments(self):
        # Create a user-owned kanban entry
        entry = KanbanEntryFactory(kanban=self.user.kanban,
                                   created_by=self.user,
                                   title="Entry with files")

        # Prepare in-memory files to upload
        file1 = SimpleUploadedFile("doc1.txt", b"Hello World 1", content_type="text/plain")
        file2 = SimpleUploadedFile("doc2.txt", b"Hello World 2", content_type="text/plain")

        # Send API request using the helper
        response = generate_request(
            api=UserKanbanEntryUpdateAPI,
            user=self.user,
            data={
                "entry_id": entry.id,
                "attachments_add": [file1, file2]
            }
        )

        self.assertEqual(response.status_code, 200, response.data)

        # Validate attachments have been saved and linked to the entry
        entry.refresh_from_db()
        self.assertIsNotNone(entry.attachments)
        self.assertEqual(entry.attachments.filesegment_set.count(), 2)
