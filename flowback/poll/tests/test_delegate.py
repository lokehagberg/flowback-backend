import json
from pprint import pprint

from rest_framework.test import APITransactionTestCase, APIRequestFactory, force_authenticate

from flowback.group.tests.factories import GroupFactory, GroupUserFactory, GroupUserDelegateFactory
from flowback.poll.tests.factories import PollFactory, PollProposalFactory, PollVotingTypeCardinalFactory, \
    PollDelegateVotingFactory
from flowback.poll.tests.utils import generate_poll_phase_kwargs
from flowback.poll.views.vote import DelegatePollVoteListAPI


class PollDelegateTests(APITransactionTestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_user_creator = GroupUserFactory(group=self.group)
        self.delegate = GroupUserDelegateFactory(group=self.group)
        self.delegator = GroupUserFactory(group=self.group)
        (self.poll_one,
         self.poll_two,
         self.poll_three) = [PollFactory(created_by=self.group_user_creator, poll_type=4,
                                         **generate_poll_phase_kwargs('delegate_vote')) for x in range(3)]

        self.poll_one_proposals = [PollProposalFactory(poll=self.poll_one,
                                                       created_by=self.group_user_creator) for x in range(3)]
        self.poll_two_proposals = [PollProposalFactory(poll=self.poll_two,
                                                       created_by=self.group_user_creator) for x in range(3)]
        self.poll_three_proposals = [PollProposalFactory(poll=self.poll_three,
                                                         created_by=self.group_user_creator) for x in range(3)]

        (self.poll_delegate_voting_one,
         self.poll_delegate_voting_two,
         self.poll_delegate_voting_three) = [PollDelegateVotingFactory(created_by=self.delegate.pool,
                                                                       poll=poll) for poll in [self.poll_one,
                                                                                               self.poll_two,
                                                                                               self.poll_three]]

        self.poll_one_delegate_votes = [PollVotingTypeCardinalFactory(author_delegate=self.poll_delegate_voting_one,
                                                                      proposal=proposal
                                                                      ) for proposal in self.poll_one_proposals[0:2]]
        self.poll_two_delegate_votes = [PollVotingTypeCardinalFactory(author_delegate=self.poll_delegate_voting_two,
                                                                      proposal=proposal
                                                                      ) for proposal in self.poll_two_proposals[1:3]]
        self.poll_three_delegate_votes = [PollVotingTypeCardinalFactory(author_delegate=self.poll_delegate_voting_three,
                                                                        proposal=proposal)
                                          for proposal in self.poll_three_proposals[0:3:2]]

    def test_delegate_poll_vote_list(self):
        factory = APIRequestFactory()
        user = self.delegator.user
        view = DelegatePollVoteListAPI.as_view()

        request = factory.get('')
        force_authenticate(request, user=user)
        response = view(request, delegate_pool_id=1)

        pprint(response.data)
