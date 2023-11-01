import json

from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from .factories import CommentFactory, CommentSectionFactory

from flowback.files.models import FileCollection, FileSegment
from ..models import CommentSection, Comment
from ..views import CommentListAPI
from ...files.tests.factories import FileCollectionFactory, FileSegmentFactory


class CommentAttachmentsTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.collection = FileCollectionFactory()
        (self.file_one,
         self.file_two,
         self.file_three) = [FileSegmentFactory(collection=self.collection) for x in range(3)]

        self.comment = CommentFactory(attachments=self.collection)

    def test_file_not_null(self):
        print(self.file_one.file)
        print(self.file_two.file)
        print(self.collection.filesegment_set.all())
        print(FileCollection.objects.get(id=self.collection.id).filesegment_set)

        factory = APIRequestFactory()
        view = CommentListAPI.as_view()

        request = factory.get('')
        force_authenticate(request, user=self.collection.created_by)
        response = view(request, comment_section_id=self.comment.comment_section_id)

        print(json.loads(response.rendered_content))
