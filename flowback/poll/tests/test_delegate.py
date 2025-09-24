import json
from pprint import pprint

from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate

from flowback.common.tests import generate_request
from flowback.group.tests.factories import GroupFactory, GroupUserFactory, GroupUserDelegateFactory
from flowback.poll.tests.factories import PollFactory, PollProposalFactory, PollVotingTypeCardinalFactory, \
    PollDelegateVotingFactory
from flowback.poll.tests.utils import generate_poll_phase_kwargs
from flowback.poll.views.vote import DelegatePollVoteListAPI


class PollDelegateTests(APITestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_user_creator = GroupUserFactory(group=self.group)
        self.delegate = GroupUserDelegateFactory(group=self.group)
        self.delegator = GroupUserFactory(group=self.group)
        
        # Create additional group users with different roles for comprehensive testing
        self.regular_group_user = GroupUserFactory(group=self.group, is_admin=False)
        self.admin_group_user = GroupUserFactory(group=self.group, is_admin=True)
        self.another_regular_user = GroupUserFactory(group=self.group, is_admin=False)
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
        # Test as delegate user
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.delegate.group_user.user,
            data=dict(group_id=self.group.id)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls

        # Verify poll IDs are in the response
        poll_ids = [item['poll_id'] for item in response.data['results']]
        self.assertIn(self.poll_one.id, poll_ids)
        self.assertIn(self.poll_two.id, poll_ids)
        self.assertIn(self.poll_three.id, poll_ids)

        # Test filtering by poll_id
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.delegate.group_user.user,
            data=dict(group_id=self.group.id, poll_id=self.poll_one.id)
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)  # Should return only poll_one
        self.assertEqual(response.data['results'][0]['poll_id'], self.poll_one.id)

        # Test filtering by delegate_pool_id
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.delegate.group_user.user,
            data=dict(group_id=self.group.id, delegate_pool_id=self.delegate.pool.id)
        )

        self.assertEqual(response.status_code, 200)
        # Should return polls where this delegate has voted
        self.assertGreaterEqual(len(response.data['results']), 1)

        # Test that ALL group users have permission to preview delegate votes
        # This expands the test as requested in the issue description
        
        # Test as regular group user (non-admin, non-delegate)
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.regular_group_user.user,
            data=dict(group_id=self.group.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls
        
        # Test as admin group user
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.admin_group_user.user,
            data=dict(group_id=self.group.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls
        
        # Test as another regular group user
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.another_regular_user.user,
            data=dict(group_id=self.group.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls
        
        # Test as delegator user
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.delegator.user,
            data=dict(group_id=self.group.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls
        
        # Test as group creator
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.group_user_creator.user,
            data=dict(group_id=self.group.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 3)  # Should return all 3 polls
        
        # Verify that all group users can also access with filters
        # Test regular user with poll_id filter
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.regular_group_user.user,
            data=dict(group_id=self.group.id, poll_id=self.poll_two.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)  # Should return only poll_two
        self.assertEqual(response.data['results'][0]['poll_id'], self.poll_two.id)
        
        # Test admin user with delegate_pool_id filter
        response = generate_request(
            api=DelegatePollVoteListAPI,
            user=self.admin_group_user.user,
            data=dict(group_id=self.group.id, delegate_pool_id=self.delegate.pool.id)
        )
        self.assertEqual(response.status_code, 200)
        # Should return polls where this delegate has voted
        self.assertGreaterEqual(len(response.data['results']), 1)
