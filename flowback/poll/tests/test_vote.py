from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase
from .factories import PollFactory, PollProposalFactory
from .utils import generate_poll_phase_kwargs
from ..models import PollDelegateVoting, PollVotingTypeCardinal
from ..views.vote import PollProposalDelegateVoteUpdateAPI
from ...files.tests.factories import FileSegmentFactory
from ...group.tests.factories import GroupFactory, GroupUserFactory, GroupUserDelegateFactory


class PollTest(APITransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.group = GroupFactory()
        self.group_user_creator = GroupUserFactory(group=self.group)
        self.delegate = GroupUserDelegateFactory(group=self.group)
        self.delegator = GroupUserFactory(group=self.group)
        (self.poll_one,
         self.poll_two,
         self.poll_three) = [PollFactory(created_by=self.group_user_creator, poll_type=4,
                                         **generate_poll_phase_kwargs('delegate_vote')) for x in range(3)]
        segment = FileSegmentFactory()
        self.poll_three.attachments = segment.collection
        self.poll_three.save()

    def test_delegate_vote(self):
        factory = APIRequestFactory()
        user = self.delegate.group_user.user
        view = PollProposalDelegateVoteUpdateAPI.as_view()

        (proposal_one,
         proposal_two) = [PollProposalFactory(created_by=self.group_user_creator, poll=self.poll_one) for x in range(2)]

        data = dict(proposals=[proposal_two.id, proposal_one.id], scores=[100, 25])

        request = factory.post('', data)
        force_authenticate(request, user=user)
        view(request, poll=self.poll_one.id)

        votes = PollDelegateVoting.objects.get(created_by=self.delegate.pool).pollvotingtypecardinal_set
        self.assertEqual(votes.filter(id__in=data['proposals']).count(), 2)
