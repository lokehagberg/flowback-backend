import json

from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase

from .factories import CommentFactory

from ..views import CommentListAPI
from ...files.tests.factories import FileCollectionFactory, FileSegmentFactory
from ...poll.tests.factories import PollFactory


class CommentAttachmentsTest(APITestCase):
    def setUp(self):
        self.collection = FileCollectionFactory()
        (self.file_one,
         self.file_two,
         self.file_three) = [FileSegmentFactory(collection=self.collection) for x in range(3)]
        self.comment = CommentFactory(attachments=self.collection)

        self.poll = PollFactory()
        (self.poll_comment_one,
         self.poll_comment_two,
         self.poll_comment_three) = [CommentFactory(comment_section=self.poll.comment_section,
                                                    attachments=(self.collection if x == 2 else None)
                                                    ) for x in range(3)]

    def test_file_not_null(self):
        factory = APIRequestFactory()
        view = CommentListAPI.as_view()

        request = factory.get('')
        force_authenticate(request, user=self.collection.created_by)
        response = view(request, comment_section_id=self.comment.comment_section_id)

        print(json.loads(response.rendered_content))
