from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from .factories import PollFactory, PollProposalFactory, PollProposalTypeScheduleFactory

from .utils import generate_poll_phase_kwargs
from ..models import PollProposal, Poll
from ..views.proposal import PollProposalListAPI, PollProposalCreateAPI, PollProposalDeleteAPI
from ...group.tests.factories import GroupFactory, GroupUserFactory, GroupTagsFactory, GroupPermissionsFactory
from ...schedule.models import ScheduleEvent
from ...user.models import User


class ProposalTest(APITestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_tag = GroupTagsFactory(group=self.group)
        self.group_user_creator = self.group.group_user_creator
        (self.group_user_one,
         self.group_user_two,
         self.group_user_three) = GroupUserFactory.create_batch(3, group=self.group)
        self.poll_schedule = PollFactory(created_by=self.group_user_one, poll_type=Poll.PollType.SCHEDULE,
                                         dynamic=True,
                                         **generate_poll_phase_kwargs('proposal'))
        self.poll_cardinal = PollFactory(created_by=self.group_user_one, poll_type=Poll.PollType.CARDINAL,
                                         **generate_poll_phase_kwargs('proposal'))
        group_users = [self.group_user_one, self.group_user_two, self.group_user_three]
        (self.poll_schedule_proposal_one,
         self.poll_schedule_proposal_two,
         self.poll_schedule_proposal_three) = [PollProposalFactory(created_by=x,
                                                                   poll=self.poll_schedule) for x in group_users]

        (self.poll_cardinal_proposal_one,
         self.poll_cardinal_proposal_two,
         self.poll_cardinal_proposal_three) = [PollProposalFactory(created_by=x,
                                                                   poll=self.poll_cardinal) for x in group_users]

    def test_proposal_list_cardinal(self):
        response = generate_request(api=PollProposalListAPI,
                                  user=self.group_user_one.user,
                                  url_params={'poll': self.poll_cardinal.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('count'), 3)

    def test_proposal_list_schedule(self):
        response = generate_request(api=PollProposalListAPI,
                                  user=self.group_user_one.user,
                                  url_params={'poll': self.poll_schedule.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('count'), 3)

    def test_proposal_list_schedule_hide_poll_users(self):
        self.group.hide_poll_users = True
        self.group.save()

        response = generate_request(api=PollProposalListAPI,
                                  user=self.group_user_one.user,
                                  url_params={'poll': self.poll_schedule.id})

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
        data = {x: y for x, y in
                dict(title=title, description=description, start_date=event__start_date, end_date=event__end_date,
                     attachments=attachments).items() if y is not None}
        return generate_request(api=PollProposalCreateAPI,
                              data=data,
                              user=user,
                              url_params={'poll': poll.id})

    def test_proposal_create(self):
        response = self.proposal_create(user=self.group_user_one.user, poll=self.poll_cardinal,
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

        response = self.proposal_create(user=self.group_user_one.user, poll=self.poll_schedule,
                                        title='Test Proposal', description='Test',
                                        event__start_date=start_date, event__end_date=end_date)
        proposal = PollProposal.objects.get(id=int(response.data))

        self.assertRaises(ObjectDoesNotExist, PollProposal.objects.get, id=proposal.id + 1)

    def test_proposal_create_no_schedule_data(self):
        response = self.proposal_create(user=self.group_user_one.user, poll=self.poll_schedule,
                                        title='Test Proposal', description='Test')

        self.assertEqual(response.status_code, 400)

    @staticmethod
    def proposal_delete(proposal, user):
        return generate_request(api=PollProposalDeleteAPI,
                              user=user,
                              url_params={'proposal': proposal.id})

    def test_proposal_delete(self):
        user = self.group_user_one.user
        proposal = self.poll_cardinal_proposal_one

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 200, response.data)

    def test_proposal_delete_no_permission(self):
        self.group_user_one.permission = GroupPermissionsFactory(author=self.group_user_one.group,
                                                                 delete_proposal=False)
        self.group_user_one.save()
        user = self.group_user_one.user
        proposal = self.poll_cardinal_proposal_one

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 400)

    def test_proposal_delete_admin(self):
        user = self.group_user_creator.user
        proposal = self.poll_cardinal_proposal_one

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 200, response.data)

    def test_proposal_schedule_delete(self):
        user = self.group_user_one.user
        proposal = self.poll_schedule_proposal_one

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 200, response.data)

    def test_proposal_schedule_delete_no_permission(self):
        self.group_user_one.permission = GroupPermissionsFactory(author=self.group_user_one.group,
                                                                 delete_proposal=False)
        self.group_user_one.save()
        user = self.group_user_one.user
        proposal = self.poll_schedule_proposal_one

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 400)

    def test_proposal_schedule_delete_admin(self):
        user = self.group_user_creator.user
        proposal = self.poll_schedule_proposal_one

        response = self.proposal_delete(proposal, user)
        self.assertEqual(response.status_code, 200, response.data)