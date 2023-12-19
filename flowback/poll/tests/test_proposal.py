import json
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase
from .factories import PollFactory, PollProposalFactory

from .utils import generate_poll_phase_kwargs
from ..models import PollProposal, Poll
from ..views.proposal import PollProposalListAPI, PollProposalCreateAPI, PollProposalDeleteAPI
from ...files.tests.factories import FileSegmentFactory
from ...group.tests.factories import GroupFactory, GroupUserFactory, GroupTagsFactory, GroupPermissionsFactory
from ...schedule.models import ScheduleEvent
from ...user.models import User


class ProposalTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.group = GroupFactory()
        self.group_tag = GroupTagsFactory(group=self.group)
        self.group_user_creator = GroupUserFactory(group=self.group, user=self.group.created_by)
        (self.group_user_one,
         self.group_user_two,
         self.group_user_three) = GroupUserFactory.create_batch(3, group=self.group)
        self.poll_schedule = PollFactory(created_by=self.group_user_one, poll_type=Poll.PollType.SCHEDULE,
                                         **generate_poll_phase_kwargs('proposal'))
        self.poll_ranking = PollFactory(created_by=self.group_user_one, poll_type=Poll.PollType.RANKING,
                                        **generate_poll_phase_kwargs('proposal'))
        group_users = [self.group_user_one, self.group_user_two, self.group_user_three]
        (self.poll_schedule_proposal_one,
         self.poll_schedule_proposal_two,
         self.poll_schedule_proposal_three) = [PollProposalFactory(created_by=x,
                                                                   poll=self.poll_schedule) for x in group_users]
        (self.poll_ranking_proposal_one,
         self.poll_ranking_proposal_two,
         self.poll_ranking_proposal_three) = [PollProposalFactory(created_by=x,
                                                                  poll=self.poll_ranking) for x in group_users]

    def test_proposal_list(self):
        factory = APIRequestFactory()
        user = self.group_user_one.user
        view = PollProposalListAPI.as_view()
        request = factory.get('')
        force_authenticate(request, user=user)

        response = view(request, poll=self.poll_schedule.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('count'), 3)

    @staticmethod
    def proposal_create(user: User,
                        poll: Poll,
                        title: str,
                        description: str,
                        event__start_date=None,
                        attachments=None,
                        event__end_date=None):
        factory = APIRequestFactory()
        view = PollProposalCreateAPI.as_view()
        data = {x: y for x, y in
                dict(title=title, description=description, start_date=event__start_date, end_date=event__end_date,
                     attachments=attachments).items() if y is not None}
        request = factory.post('', data=data)
        force_authenticate(request, user)
        return view(request, poll=poll.id)

    def test_proposal_create(self):
        response = self.proposal_create(user=self.group_user_one.user, poll=self.poll_ranking,
                                        title='Test Proposal', description='Test')

        self.assertEqual(response.status_code, 200, response.data)
        proposal = PollProposal.objects.get(id=int(response.data))

        self.assertEqual(proposal.title, 'Test Proposal')
        self.assertEqual(proposal.description, 'Test')

    def test_proposal_create_schedule(self):
        start_date = timezone.now() + timezone.timedelta(hours=1)
        end_date = timezone.now() + timezone.timedelta(hours=2)
        response = self.proposal_create(user=self.group_user_one.user, poll=self.poll_schedule,
                                        title='Test Proposal', description='Test',
                                        event__start_date=start_date, event__end_date=end_date)

        self.assertEqual(response.status_code, 200, response.data)
        proposal = PollProposal.objects.get(id=int(response.data))

        self.assertEqual(proposal.title, 'Test Proposal')
        self.assertEqual(proposal.description, 'Test')
        self.assertEqual(proposal.pollproposaltypeschedule.event.start_date, start_date)
        self.assertEqual(proposal.pollproposaltypeschedule.event.end_date, end_date)

    def test_proposal_create_no_schedule_data(self):
        response = self.proposal_create(user=self.group_user_one.user, poll=self.poll_schedule,
                                        title='Test Proposal', description='Test')

        self.assertEqual(response.status_code, 400)

    @staticmethod
    def proposal_delete(proposal, user):
        factory = APIRequestFactory()
        view = PollProposalDeleteAPI.as_view()
        request = factory.post('')
        force_authenticate(request, user=user)

        return view(request, proposal=proposal.id)

    def test_proposal_delete(self):
        user = self.group_user_one.user
        proposal = self.poll_ranking_proposal_one

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 200, response.data)

    def test_proposal_delete_no_permission(self):
        self.group_user_one.permission = GroupPermissionsFactory(author=self.group_user_one.group,
                                                                 delete_proposal=False)
        self.group_user_one.save()
        user = self.group_user_one.user
        proposal = self.poll_ranking_proposal_one

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 400)

    def test_proposal_delete_admin(self):
        user = self.group_user_creator.user
        proposal = self.poll_ranking_proposal_one

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 200, response.data)

    def test_proposal_schedule_delete(self):
        user = self.group_user_one.user
        proposal = self.poll_schedule_proposal_one
        event_id = proposal.pollproposaltypeschedule.event.id

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScheduleEvent.objects.filter(id=event_id).exists())

    def test_proposal_schedule_delete_no_permission(self):
        self.group_user_one.permission = GroupPermissionsFactory(author=self.group_user_one.group,
                                                                 delete_proposal=False)
        self.group_user_one.save()
        user = self.group_user_one.user
        proposal = self.poll_schedule_proposal_one
        event_id = proposal.pollproposaltypeschedule.event.id

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(ScheduleEvent.objects.filter(id=event_id).exists())

    def test_proposal_schedule_delete_admin(self):
        user = self.group_user_creator.user
        proposal = self.poll_schedule_proposal_one
        event_id = proposal.pollproposaltypeschedule.event.id
        self.assertTrue(ScheduleEvent.objects.filter(id=event_id).exists())

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(ScheduleEvent.objects.filter(id=event_id).exists())
