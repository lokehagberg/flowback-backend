from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from flowback.files.services import upload_collection, update_collection
from flowback.user.tests.factories import UserFactory


class TestFileCollection(APITestCase):
    def setUp(self):
        self.user_one = UserFactory()
        self.user_two = UserFactory()
        self.user_three = UserFactory()

    def test_filecollection_create(self):
        files = [SimpleUploadedFile(name='test.txt', content=b'hi', content_type='text/plain') for _ in range(8)]

        collection = upload_collection(user_id=self.user_one.id,
                                       file=files,
                                       upload_to='test/')

        self.assertTrue(collection)
        self.assertEqual(collection.created_by, self.user_one)
        self.assertEqual(collection.filesegment_set.count(), 8)

        return collection

    def test_filecollection_update(self):
        collection = self.test_filecollection_create()
        attachments_remove = [i.id for i in collection.filesegment_set.all()[:3]]  # Remove index 0, 1, 2
        attachments_add = [SimpleUploadedFile(name='test.txt', content=b'hi', content_type='text/plain') for _ in range(2)]

        update_collection(user_id=self.user_one.id,
                          file_collection_id=collection.id,
                          attachments_remove=attachments_remove,
                          attachments_add=attachments_add,
                          upload_to='test/')

        self.assertEqual(collection.filesegment_set.count(), 7)
        self.assertEqual(collection.filesegment_set.filter(id__in=attachments_remove).count(), 0)
