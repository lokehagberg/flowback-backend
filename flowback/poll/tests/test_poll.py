import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase
from .factories import PollFactory, PollProposalFactory, PollPredictionStatementFactory

from .utils import generate_poll_phase_kwargs
from ..models import Poll
from ..services.poll import poll_fast_forward, poll_create
from ..views.poll import PollListApi, PollCreateAPI, PollUpdateAPI, PollDeleteAPI
from ...comment.tests.factories import CommentFactory
from ...common.tests import generate_request
from ...files.tests.factories import FileSegmentFactory
from ...group.models import GroupUser
from ...group.tests.factories import GroupFactory, GroupUserFactory, GroupTagsFactory
from ...group.views.group import GroupNotificationSubscribeAPI
from ...notification.models import NotificationChannel, NotificationObject, Notification
from ...notification.views import NotificationListAPI
from ...user.models import User


class PollTest(APITestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_tag = GroupTagsFactory(group=self.group)
        self.group_user_creator = GroupUser.objects.get(user=self.group.created_by, group=self.group)
        (self.group_user_one,
         self.group_user_two,
         self.group_user_three) = GroupUserFactory.create_batch(3, group=self.group)
        (self.poll_one,
         self.poll_two,
         self.poll_three) = [PollFactory(created_by=x, pinned=False) for x in
                             [self.group_user_creator, self.group_user_one,
                              self.group_user_two]]
        segment = FileSegmentFactory()
        self.poll_three.attachments = segment.collection
        self.poll_three.save()

    def test_list_polls(self):
        self.poll_three.pinned = True
        self.poll_three.save()

        CommentFactory.create_batch(17, comment_section=self.poll_one.comment_section)
        PollProposalFactory.create_batch(12, poll=self.poll_one)
        PollProposalFactory.create_batch(12, poll=self.poll_two)
        PollPredictionStatementFactory.create_batch(15, poll=self.poll_one)

        response = generate_request(api=PollListApi,
                                    data=dict(order_by='pinned,start_date_asc'),
                                    user=self.group_user_creator.user)

        print(response.data)

        self.assertTrue(response.data['results'][0]['pinned'])
        self.assertEqual(response.data['count'], 3)
        self.assertGreater(response.data['results'][2]['start_date'], response.data['results'][1]['start_date'])
        self.assertGreater(response.data['results'][0]['start_date'], response.data['results'][2]['start_date'])
        self.assertEqual(response.data['results'][1]['total_comments'], 17)
        self.assertEqual(response.data['results'][1]['total_proposals'], 12)
        self.assertEqual(response.data['results'][1]['total_predictions'], 15)

    def test_list_polls_hide_users(self):
        self.group.hide_poll_users = True
        self.group.save()

        response = generate_request(api=PollListApi,
                                    data=dict(order_by='pinned,start_date_asc'),
                                    user=self.group_user_creator.user)

        self.assertTrue(all([not x['created_by'] for x in response.data['results']]),
                        [[bool(x['created_by']), x['group_id']] for x in response.data['results']])

    def test_create_poll(self):
        factory = APIRequestFactory()
        user = self.group_user_creator.user
        view = ~PollCreateAPI.as_view()

        data = dict(title='test title', description='test description', poll_type=4, public=True, tag=self.group_tag.id,
                    pinned=False, dynamic=False, attachments=[SimpleUploadedFile('test.jpg', b'test')],
                    **generate_poll_phase_kwargs('base'))
        request = factory.post('', data=data)
        force_authenticate(request, user)
        response = view(request, group_id=self.group.id)  # Success

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_poll_notification(self):
        subscriber = self.group_user_one
        poll_creator = self.group_user_two

        # Subscribe group_user_one to the group notification channel
        generate_request(GroupNotificationSubscribeAPI,
                         data=dict(tags=['poll']),
                         user=subscriber.user,
                         url_params=dict(group_id=self.group.id))

        # Check there's no notifications ahead of the test
        response = generate_request(NotificationListAPI,
                                    data=dict(order_by='timestamp_desc'),
                                    user=subscriber.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['count'], 0)

        data = dict(title='notification test poll', description='testing notifications',
                    poll_type=4, public=True, tag=self.group_tag.id,
                    pinned=False, dynamic=False, attachments=[SimpleUploadedFile('test.jpg', b'test')],
                    **generate_poll_phase_kwargs('base'))

        # Use generate_request to create the poll
        response = generate_request(
            api=PollCreateAPI,
            data=data,
            url_params=dict(group_id=self.group.id),
            user=poll_creator.user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if the subscriber received a notification
        notification = Notification.objects.get(
            user=subscriber.user,
            notification_object__channel=self.group.notification_channel,
            notification_object__tag="poll",
            notification_object__data__poll_id=response.data,
            notification_object__action=NotificationObject.Action.CREATED,
        )

        # Also check if the API returns the Notification
        response = generate_request(NotificationListAPI,
                                    data=dict(order_by='timestamp_desc',
                                              object_id=notification.notification_object.id),
                                    user=subscriber.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['count'], 1)

    def test_create_poll_below_phase_space_minimum(self):
        phases = generate_poll_phase_kwargs('base')
        phases['proposal_end_date'] -= timezone.timedelta(hours=2)

        data = dict(title='test title', description='test description', poll_type=4, public=True, tag=self.group_tag.id,
                    pinned=False, dynamic=False, attachments=[SimpleUploadedFile('test.jpg', b'test')])

        # Test phase in wrong order
        with self.assertRaises(ValidationError):
            poll_create(user_id=self.group_user_one.user.id,
                        group_id=self.group_user_one.group.id,
                        **data, **phases)

        group = self.group_user_one.group
        phases['proposal_end_date'] += timezone.timedelta(hours=2)
        group.poll_phase_minimum_space += 100000000
        group.save()

        with self.assertRaises(ValidationError):
            poll_create(user_id=self.group_user_one.user.id,
                        group_id=self.group_user_one.group.id,
                        **data, **phases)

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

        data = dict(title='new_title', description='new_description')
        request = factory.post('', data=data)
        force_authenticate(request, user)

        response = view(request, poll=self.poll_two.id)
        self.assertEqual(response.status_code, 200, response.rendered_content)

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

    @staticmethod
    def delete_poll(poll: Poll, user: User):
        factory = APIRequestFactory()
        view = PollDeleteAPI.as_view()
        request = factory.post('')
        force_authenticate(request, user=user)

        return view(request, poll=poll.id)

    def test_delete_poll_success(self):
        poll = PollFactory(created_by=self.group_user_one, **generate_poll_phase_kwargs(poll_start_phase='waiting'))
        response = self.delete_poll(poll=poll, user=self.group_user_one.user)

        self.assertTrue(response.status_code == 200, msg=response.data)

    def test_delete_poll_in_progress(self):
        poll = PollFactory(created_by=self.group_user_one, **generate_poll_phase_kwargs(poll_start_phase='proposal'))
        response = self.delete_poll(poll=poll, user=self.group_user_one.user)

        self.assertTrue(response.status_code == 400)
        self.assertTrue(Poll.objects.filter(id=poll.id).exists())

    def test_delete_poll_in_progress_admin(self):
        poll = PollFactory(created_by=self.group_user_one, **generate_poll_phase_kwargs(poll_start_phase='proposal'))
        response = self.delete_poll(poll=poll, user=self.group_user_creator.user)

        self.assertTrue(response.status_code == 200)
        self.assertTrue(not Poll.objects.filter(id=poll.id).exists())
