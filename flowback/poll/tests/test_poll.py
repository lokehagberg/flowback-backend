import json

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase
from .factories import PollFactory, PollPriorityFactory

from .utils import generate_poll_phase_kwargs
from ..models import Poll, PollPriority
from ..selectors.poll import poll_list
from ..views.poll import PollListApi, PollCreateAPI, PollUpdateAPI, PollDeleteAPI, PollPriorityUpdateAPI
from ..models import Poll
from ..services.poll import poll_fast_forward
from ...files.tests.factories import FileSegmentFactory
from ...group.tests.factories import GroupFactory, GroupUserFactory, GroupTagsFactory
from ...user.models import User


class PollTest(APITransactionTestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_tag = GroupTagsFactory(group=self.group)
        self.group_user_creator = GroupUserFactory(group=self.group, user=self.group.created_by)
        (self.group_user_one,
         self.group_user_two,
         self.group_user_three) = GroupUserFactory.create_batch(3, group=self.group)
        (self.poll_one,
         self.poll_two,
         self.poll_three) = [PollFactory(created_by=x) for x in [self.group_user_creator, self.group_user_one,
                                                                 self.group_user_two]]
        segment = FileSegmentFactory()
        self.poll_three.attachments = segment.collection
        self.poll_three.save()

    def test_list_polls(self):
        factory = APIRequestFactory()
        user = self.group_user_creator.user
        view = PollListApi.as_view()

        request = factory.get('')
        force_authenticate(request, user)
        response = view(request, group_id=self.group.id)

        self.assertTrue(len(json.loads(response.rendered_content)['results']) == 3)

    def test_create_poll(self):
        factory = APIRequestFactory()
        user = self.group_user_creator.user
        view = PollCreateAPI.as_view()

        data = dict(title='test title', description='test description', poll_type=1001, public=True, tag=self.group_tag.id,
                    pinned=False, dynamic=False, attachments=[SimpleUploadedFile('test.jpg', b'test')],
                    **generate_poll_phase_kwargs('base'))
        request = factory.post('', data=data)
        force_authenticate(request, user)
        response = view(request, group_id=self.group.id)  # Success

        data = dict(title='test title', description='test description', poll_type=4,
                    parent_id=response.data, public=True, tag=self.group_tag.id,
                    pinned=False, dynamic=False, attachments=[SimpleUploadedFile('test.jpg', b'test')],
                    **generate_poll_phase_kwargs('base'))

        request = factory.post('', data=data)
        force_authenticate(request, user)
        response = view(request, group_id=self.group.id)  # Success
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_failing_poll(self):
        factory = APIRequestFactory()
        user = self.group_user_creator.user
        view = PollCreateAPI.as_view()

        data = dict(title='test title', description='test description', poll_type=3, public=True, tag=self.group_tag.id,
                    pinned=False, dynamic=False, attachments=[SimpleUploadedFile('test.jpg', b'test')],
                    **generate_poll_phase_kwargs('base'))
        request = factory.post('', data=data)
        force_authenticate(request, user)

        response = view(request, group_id=self.group.id)  # Success

        self.assertTrue(json.loads(response.rendered_content).get('detail')[0] == 'Schedule poll must be dynamic',
                        json.loads(response.rendered_content))

    def test_update_poll(self):
        factory = APIRequestFactory()
        user = self.group_user_one.user
        view = PollUpdateAPI.as_view()

        data = dict(title='new_title', description='new_description', pinned=False)
        request = factory.post('', data=data)
        force_authenticate(request, user)

        response = view(request, poll=self.poll_two.id)
        self.assertTrue(response.status_code == 200, response.rendered_content)

        self.poll_two.refresh_from_db()
        self.assertTrue(self.poll_two.title == 'new_title')
        self.assertTrue(self.poll_two.description == 'new_description')
        self.assertTrue(not self.poll_two.pinned)

    def test_update_poll_pinned_permission_denied(self):
        factory = APIRequestFactory()
        user = self.group_user_one.user
        view = PollUpdateAPI.as_view()

        data = dict(title='new_title', description='new_description', pinned=True)
        request = factory.post('', data=data)
        force_authenticate(request, user)

        response = view(request, poll=self.poll_two.id)
        self.assertTrue(response.status_code == 400, response.rendered_content)

        self.poll_two.refresh_from_db()
        self.assertTrue(not self.poll_two.pinned)

    def test_update_poll_admin(self):
        factory = APIRequestFactory()
        user = self.group_user_creator.user
        view = PollUpdateAPI.as_view()

        data = dict(title='new_title', description='new_description', pinned=True)
        request = factory.post('', data=data)
        force_authenticate(request, user)

        response = view(request, poll=self.poll_two.id)
        self.assertTrue(response.status_code == 200, response.rendered_content)

        self.poll_two.refresh_from_db()
        self.assertTrue(self.poll_two.title == 'new_title')
        self.assertTrue(self.poll_two.description == 'new_description')
        self.assertTrue(self.poll_two.pinned)

    def test_poll_phase_fast_forward(self):
        poll = PollFactory(created_by__is_admin=True,
                           allow_fast_forward=True,
                           poll_type=4,
                           dynamic=False,
                           **generate_poll_phase_kwargs())
        poll_fast_forward(user_id=poll.created_by.user.id, poll_id=poll.id, phase='vote')

        poll.refresh_from_db()
        self.assertEqual('vote', poll.current_phase)

    def delete_poll(self, poll: Poll, user: User):
        factory = APIRequestFactory()
        view = PollDeleteAPI.as_view()
        request = factory.post('')
        force_authenticate(request, user=user)

        return view(request, poll=poll.id)

    def test_delete_poll_success(self):
        poll = PollFactory(created_by=self.group_user_one, **generate_poll_phase_kwargs(poll_start_phase='waiting'))
        response = self.delete_poll(poll, user=self.group_user_one.user)

        self.assertTrue(response.status_code == 200)
        self.assertTrue(not Poll.objects.filter(id=poll.id).exists())

    def test_delete_poll_in_progress(self):
        poll = PollFactory(created_by=self.group_user_one, **generate_poll_phase_kwargs(poll_start_phase='proposal'))
        response = self.delete_poll(poll, user=self.group_user_one.user)

        self.assertTrue(response.status_code == 400)
        self.assertTrue(Poll.objects.filter(id=poll.id).exists())

    def test_delete_poll_in_progress_admin(self):
        poll = PollFactory(created_by=self.group_user_one, **generate_poll_phase_kwargs(poll_start_phase='proposal'))
        response = self.delete_poll(poll, user=self.group_user_creator.user)

        self.assertTrue(response.status_code == 200)
        self.assertTrue(not Poll.objects.filter(id=poll.id).exists())

    def test_poll_priority_list(self):
        vote_one = PollPriorityFactory(poll=self.poll_one, group_user=self.group_user_one, score=1)
        vote_two = PollPriorityFactory(poll=self.poll_one, group_user=self.group_user_two, score=1)
        vote_three = PollPriorityFactory(poll=self.poll_one, group_user=self.group_user_three, score=-1)

        polls = poll_list(fetched_by=self.group_user_one.user, group_id=self.poll_one.created_by.group.id)

        self.assertEqual(polls.get(id=self.poll_one.id).priority, 1)
        self.assertEqual(polls.get(id=self.poll_two.id).priority, 0)
        self.assertEqual(polls.get(id=self.poll_one.id).user_priority, 1)
        self.assertEqual(polls.get(id=self.poll_two.id).user_priority, None)

    def test_poll_priority_update(self):
        def vote(score: int):
            factory = APIRequestFactory()
            view = PollPriorityUpdateAPI.as_view()
            data = dict(score=score)
            request = factory.post('', data=data)
            force_authenticate(request, user=self.group_user_one.user)
            view(request, poll_id=self.poll_one.id)

            if score != 0:
                self.assertEqual(PollPriority.objects.get(poll_id=self.poll_one.id,
                                                          group_user=self.group_user_one).score, score)

            else:
                self.assertFalse(PollPriority.objects.filter(poll_id=self.poll_one.id,
                                                             group_user=self.group_user_one).exists())

        vote(1)
        vote(-1)
        vote(0)
