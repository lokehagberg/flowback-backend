import json

from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from flowback.comment.models import Comment
from .factories import PollFactory
from ...comment.tests.factories import CommentFactory
from ...files.tests.factories import FileCollectionFactory, FileSegmentFactory
from ...poll.views.comment import PollCommentCreateAPI, PollCommentListAPI


class PollCommentTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.collection = FileCollectionFactory()
        (self.file_one,
         self.file_two,
         self.file_three) = [FileSegmentFactory(collection=self.collection) for x in range(3)]

        self.poll = PollFactory()
        (self.poll_comment_one,
         self.poll_comment_two,
         self.poll_comment_three) = [CommentFactory(comment_section=self.poll.comment_section,
                                                    attachments=(self.collection if x == 2 else None)
                                                    ) for x in range(3)]

    def test_poll_comment_create_no_attachments(self):
        factory = APIRequestFactory()
        view = PollCommentCreateAPI.as_view()
        data = dict(message='hello')

        request = factory.post('', data=data)
        force_authenticate(request, user=self.poll.created_by.user)
        response = view(request, poll=self.poll.id)

        comment_id = int(json.loads(response.rendered_content))
        comment = Comment.objects.get(id=comment_id)
        self.assertEqual(comment.attachments, None)

    def test_poll_comment_create_with_attachments(self):
        factory = APIRequestFactory()
        view = PollCommentCreateAPI.as_view()

        # request without image
        data = dict(message='hello',
                    attachments=[SimpleUploadedFile('test.txt', b'test message'),
                                 SimpleUploadedFile('test.txt', b'another test message')])

        request = factory.post('', data=data)
        force_authenticate(request, user=self.poll.created_by.user)
        response = view(request, poll=self.poll.id)

        comment_id = int(json.loads(response.rendered_content))
        comment = Comment.objects.get(id=comment_id)
        files = comment.attachments.filesegment_set

        data_ex = dict(message='hello_2',
                       attachments=[SimpleUploadedFile('test.txt', b'test message'),
                                    SimpleUploadedFile('test.txt', b'another test message')])

        request_ex = factory.post('', data=data_ex)
        force_authenticate(request_ex, user=self.poll.created_by.user)
        response_ex = view(request_ex, poll=self.poll.id)

        comment_id_ex = int(json.loads(response_ex.rendered_content))
        comment_ex = Comment.objects.get(id=comment_id_ex)
        files_ex = comment_ex.attachments.filesegment_set

        self.assertEqual(all('test' not in x.updated_at for x in files.all()), True)
        self.assertEqual(all('test' not in x.updated_at for x in files_ex.all()), True)
        self.assertEqual(files.count(), len(data['attachments']))

    def test_poll_comment_list(self):
        factory = APIRequestFactory()
        view = PollCommentListAPI.as_view()

        request = factory.get('')
        force_authenticate(request, user=self.poll.created_by.user)
        response = view(request, poll=self.poll.id)

        data = json.loads(response.rendered_content)
        print(data)
