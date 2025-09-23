from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase
from .factories import PollFactory, PollProposalFactory
from .utils import generate_poll_phase_kwargs
from ..models import PollDelegateVoting, PollVotingTypeCardinal, Poll, PollProposal, PollVoting, \
    PollVotingTypeForAgainst
from ..tasks import poll_proposal_vote_count
from ..views.vote import (PollProposalDelegateVoteUpdateAPI,
                          PollProposalVoteUpdateAPI,
                          PollProposalVoteListAPI)
from ...common.tests import generate_request
from ...files.tests.factories import FileSegmentFactory
from ...group.tests.factories import GroupFactory, GroupUserFactory, GroupUserDelegateFactory, GroupTagsFactory, \
    GroupUserDelegatePoolFactory, GroupUserDelegatorFactory, GroupPermissionsFactory
from ...user.models import User


class PollVoteTest(APITestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.group_tag = GroupTagsFactory(group=self.group)
        self.group_user_creator = self.group.group_user_creator
        (self.group_user_one,
         self.group_user_two,
         self.group_user_three) = GroupUserFactory.create_batch(3, group=self.group)
        self.poll_schedule = PollFactory(created_by=self.group_user_one, poll_type=Poll.PollType.SCHEDULE,
                                         tag=GroupTagsFactory(group=self.group), **generate_poll_phase_kwargs('vote'))
        self.poll_cardinal = PollFactory(created_by=self.group_user_one, poll_type=Poll.PollType.CARDINAL,
                                         tag=GroupTagsFactory(group=self.group), **generate_poll_phase_kwargs('vote'))
        self.group_users = [self.group_user_one, self.group_user_two, self.group_user_three]
        (self.poll_schedule_proposal_one,
         self.poll_schedule_proposal_two,
         self.poll_schedule_proposal_three) = [PollProposalFactory(created_by=x,
                                                                   poll=self.poll_schedule) for x in self.group_users]
        (self.poll_cardinal_proposal_one,
         self.poll_cardinal_proposal_two,
         self.poll_cardinal_proposal_three) = [PollProposalFactory(created_by=x,
                                                                   poll=self.poll_cardinal) for x in self.group_users]

    @staticmethod
    def cardinal_vote_update(user: User, poll: Poll, proposals: list[PollProposal], scores: list[int], delegate=False):
        api = PollProposalVoteUpdateAPI if not delegate else PollProposalDelegateVoteUpdateAPI
        data = dict(proposals=[x.id for x in proposals], scores=scores)
        return generate_request(api=api, data=data, user=user, url_params=dict(poll=poll.id))

    def test_vote_update_cardinal(self):
        user = self.group_user_one.user
        proposals = [self.poll_cardinal_proposal_three, self.poll_cardinal_proposal_one]
        scores = [23, 980]
        response = self.cardinal_vote_update(user, self.poll_cardinal, proposals, scores)

        self.assertEqual(response.status_code, 200, response.data)

        voting_account = PollVoting.objects.get(created_by=self.group_user_one)
        self.assertEqual(PollVotingTypeCardinal.objects.get(author=voting_account,
                                                            proposal_id=proposals[0].id).raw_score, scores[0])
        self.assertEqual(PollVotingTypeCardinal.objects.get(author=voting_account,
                                                            proposal_id=proposals[1].id).raw_score, scores[1])

    def test_vote_update_cardinal_reset(self):
        self.test_vote_update_cardinal()

        user = self.group_user_one.user
        proposals = [self.poll_cardinal_proposal_one,
                     self.poll_cardinal_proposal_three,
                     self.poll_cardinal_proposal_two]
        scores = [91, 74, 228]
        response = self.cardinal_vote_update(user, self.poll_cardinal, proposals, scores)

        self.assertEqual(response.status_code, 200, response.data)
        voting_account = PollVoting.objects.get(created_by=self.group_user_one)

        for x in range(3):
            self.assertEqual(PollVotingTypeCardinal.objects.get(author=voting_account,
                                                                proposal_id=proposals[x].id).raw_score, scores[x])

    def test_vote_update_cardinal_duplicate(self):
        user = self.group_user_one.user
        proposals = [self.poll_cardinal_proposal_three,
                     self.poll_cardinal_proposal_one,
                     self.poll_cardinal_proposal_one]
        scores = [23, 980, 22]
        response = self.cardinal_vote_update(user, self.poll_cardinal, proposals, scores)

        self.assertEqual(response.status_code, 400)

    def test_vote_count_cardinal(self):
        user = self.group_user_two.user
        proposals = [self.poll_cardinal_proposal_two, self.poll_cardinal_proposal_three]
        scores = [78, 22]
        response = self.cardinal_vote_update(user, self.poll_cardinal, proposals, scores)
        self.assertEqual(response.status_code, 200, response.data)

        user = self.group_user_one.user
        proposals = [self.poll_cardinal_proposal_three, self.poll_cardinal_proposal_one]
        scores = [23, 980]
        response = self.cardinal_vote_update(user, self.poll_cardinal, proposals, scores)
        self.assertEqual(response.status_code, 200, response.data)

        # two delegators under group_user_three
        delegate = GroupUserDelegateFactory(group=self.group, group_user=self.group_user_three)
        delegators = GroupUserDelegatorFactory.create_batch(2,
                                                            group=self.group,
                                                            delegate_pool=delegate.pool)

        [delegator.tags.add(self.poll_cardinal.tag) for delegator in delegators]
        self.assertTrue(all([delegator.tags.filter(id=self.poll_cardinal.tag.id).exists() for delegator in delegators]))

        user = self.group_user_three.user
        proposals = [self.poll_cardinal_proposal_three, self.poll_cardinal_proposal_two]
        scores = [14, 86]

        # User 3
        response = self.cardinal_vote_update(user, self.poll_cardinal, proposals, scores)
        self.assertEqual(response.status_code, 200, response.data)

        Poll.objects.filter(id=self.poll_cardinal.id).update(**generate_poll_phase_kwargs('delegate_vote'))

        # Delegate User 3
        response = self.cardinal_vote_update(user, self.poll_cardinal, proposals, scores, delegate=True)
        self.assertEqual(response.status_code, 200, response.data)

        Poll.objects.filter(id=self.poll_cardinal.id).update(**generate_poll_phase_kwargs('result'))
        poll_proposal_vote_count(poll_id=self.poll_cardinal.id)
        self.assertNotEqual(Poll.objects.get(id=self.poll_cardinal.id).status, -1)

        self.poll_cardinal_proposal_one.refresh_from_db()
        self.poll_cardinal_proposal_two.refresh_from_db()
        self.poll_cardinal_proposal_three.refresh_from_db()

        self.assertEqual(self.poll_cardinal_proposal_one.score, 980)
        self.assertEqual(self.poll_cardinal_proposal_two.score, 336)
        self.assertEqual(self.poll_cardinal_proposal_three.score, 87)

    @staticmethod
    def schedule_vote_update(user: User, poll: Poll, proposals: list[PollProposal]):
        factory = APIRequestFactory()
        view = PollProposalVoteUpdateAPI.as_view()
        data = dict(proposals=[x.id for x in proposals])
        request = factory.post('', data=data)
        force_authenticate(request, user)
        return view(request, poll=poll.id)

    def test_vote_update_schedule(self):
        user = self.group_user_one.user
        proposals = [self.poll_schedule_proposal_three, self.poll_schedule_proposal_one]
        response = self.schedule_vote_update(user, self.poll_schedule, proposals)

        self.assertEqual(response.status_code, 200, response.data)

        voting_account = PollVoting.objects.get(created_by=self.group_user_one)
        for x in range(2):
            self.assertEqual(PollVotingTypeForAgainst.objects.get(author=voting_account,
                                                                  proposal_id=proposals[x].id).vote, True)

    def test_vote_update_schedule_reset(self):
        self.test_vote_update_schedule()
        user = self.group_user_one.user
        proposals = [self.poll_schedule_proposal_one,
                     self.poll_schedule_proposal_two]
        response = self.schedule_vote_update(user, self.poll_schedule, proposals)

        self.assertEqual(response.status_code, 200, response.data)
        voting_account = PollVoting.objects.get(created_by=self.group_user_one)

        for x in range(2):
            self.assertEqual(PollVotingTypeForAgainst.objects.get(author=voting_account,
                                                                  proposal_id=proposals[x].id).vote, True)

        # Check if previous vote successfully deleted
        self.assertFalse(PollVotingTypeForAgainst.objects.filter(author=voting_account,
                                                                 proposal_id=self.poll_schedule_proposal_three
                                                                 ).exists())

    def test_vote_update_schedule_duplicate(self):
        user = self.group_user_one.user
        proposals = [self.poll_schedule_proposal_three,
                     self.poll_schedule_proposal_one,
                     self.poll_schedule_proposal_one]
        response = self.schedule_vote_update(user, self.poll_schedule, proposals)

        self.assertEqual(response.status_code, 400)

    def test_vote_count_schedule(self):
        user = self.group_user_two.user
        proposals = [self.poll_schedule_proposal_two, self.poll_schedule_proposal_three]
        response = self.schedule_vote_update(user, self.poll_schedule, proposals)
        self.assertEqual(response.status_code, 200, response.data)

        user = self.group_user_one.user
        proposals = [self.poll_schedule_proposal_three, self.poll_schedule_proposal_one]
        response = self.schedule_vote_update(user, self.poll_schedule, proposals)
        self.assertEqual(response.status_code, 200, response.data)

        user = self.group_user_three.user
        proposals = [self.poll_schedule_proposal_three, self.poll_schedule_proposal_two]
        response = self.schedule_vote_update(user, self.poll_schedule, proposals)
        self.assertEqual(response.status_code, 200, response.data)

        Poll.objects.filter(id=self.poll_schedule.id).update(**generate_poll_phase_kwargs('result'))
        poll_proposal_vote_count(poll_id=self.poll_schedule.id)
        poll_proposal_vote_count(poll_id=self.poll_schedule.id)  # Test if duplicate event generates

        self.poll_schedule_proposal_one.refresh_from_db()
        self.poll_schedule_proposal_two.refresh_from_db()
        self.poll_schedule_proposal_three.refresh_from_db()

        self.assertEqual(self.poll_schedule_proposal_one.score, 1)
        self.assertEqual(self.poll_schedule_proposal_two.score, 2)
        self.assertEqual(self.poll_schedule_proposal_three.score, 3)

        event = self.poll_schedule.created_by.group.schedule.scheduleevent_set.get(
            origin_name=self.poll_schedule.schedule_origin,
            origin_id=self.poll_schedule.id)

        self.assertEqual(event.start_date, self.poll_schedule_proposal_three.pollproposaltypeschedule.event.start_date)
        self.assertEqual(event.end_date, self.poll_schedule_proposal_three.pollproposaltypeschedule.event.end_date)


class PollDelegateVoteTest(APITestCase):
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

    def test_delegate_vote_count_with_permissions(self):
        """Test poll_proposal_vote_count where delegate has delegators with and without voting permissions"""
        # Create a poll with tag
        tag = GroupTagsFactory(group=self.group)
        poll = PollFactory(created_by=self.group_user_creator, poll_type=Poll.PollType.CARDINAL, tag=tag,
                          **generate_poll_phase_kwargs('delegate_vote'))
        
        # Create proposals for the poll
        proposal_one = PollProposalFactory(created_by=self.group_user_creator, poll=poll)
        proposal_two = PollProposalFactory(created_by=self.group_user_creator, poll=poll)
        
        # Create a delegate
        delegate = GroupUserDelegateFactory(group=self.group)
        
        # Create permissions - one allowing vote, one denying vote
        permission_allow_vote = GroupPermissionsFactory(author=self.group, allow_vote=True)
        permission_deny_vote = GroupPermissionsFactory(author=self.group, allow_vote=False)
        
        # Create delegators with different permissions
        # 2 delegators with voting permission
        delegator_with_permission_1 = GroupUserFactory(group=self.group, permission=permission_allow_vote)
        delegator_with_permission_2 = GroupUserFactory(group=self.group, permission=permission_allow_vote)

        # 2 delegators without voting permission
        delegator_without_permission_1 = GroupUserFactory(group=self.group, permission=permission_deny_vote)
        delegator_without_permission_2 = GroupUserFactory(group=self.group, permission=permission_deny_vote)

        # Create delegator relationships
        delegator_pool_1 = GroupUserDelegatorFactory(group=self.group, delegator=delegator_with_permission_1,
                                                     delegate_pool=delegate.pool)
        delegator_pool_2 = GroupUserDelegatorFactory(group=self.group, delegator=delegator_with_permission_2,
                                                     delegate_pool=delegate.pool)
        delegator_pool_3 = GroupUserDelegatorFactory(group=self.group, delegator=delegator_without_permission_1,
                                                     delegate_pool=delegate.pool)
        delegator_pool_4 = GroupUserDelegatorFactory(group=self.group, delegator=delegator_without_permission_2,
                                                     delegate_pool=delegate.pool)

        # Add tag to all delegators
        for delegator_pool in [delegator_pool_1, delegator_pool_2, delegator_pool_3, delegator_pool_4]:
            delegator_pool.tags.add(tag)

        # Have the delegate vote
        factory = APIRequestFactory()
        user = delegate.group_user.user
        view = PollProposalDelegateVoteUpdateAPI.as_view()
        data = dict(proposals=[proposal_one.id, proposal_two.id], scores=[100, 50])

        request = factory.post('', data)
        force_authenticate(request, user=user)
        response = view(request, poll=poll.id)
        self.assertEqual(response.status_code, 200)

        # Verify delegate voting record was created
        delegate_vote = PollDelegateVoting.objects.get(created_by=delegate.pool, poll=poll)
        self.assertIsNotNone(delegate_vote)

        # Change poll phase to result phase and call vote count
        Poll.objects.filter(id=poll.id).update(**generate_poll_phase_kwargs('result'))
        poll_proposal_vote_count(poll_id=poll.id)

        # Refresh delegate vote to get updated mandate
        delegate_vote.refresh_from_db()

        # Verify that only delegators with voting permission are counted
        # Should be 2 (delegators with permission) - only delegators count toward mandate, not the delegate
        expected_mandate = 2  # Only the 2 delegators with voting permission should be counted
        self.assertEqual(delegate_vote.mandate, expected_mandate, 
                        f"Expected mandate of {expected_mandate} but got {delegate_vote.mandate}")
        
        # Verify proposals got correct scores based on only counting delegators with permission
        proposal_one.refresh_from_db()
        proposal_two.refresh_from_db()
        
        # Each delegator with permission contributes their weight to the delegate's vote
        # Delegate vote: proposal_one=100, proposal_two=50
        # With mandate of 2, final scores should be: proposal_one=200, proposal_two=100
        self.assertEqual(proposal_one.score, 200, f"Expected proposal_one score of 200 but got {proposal_one.score}")
        self.assertEqual(proposal_two.score, 100, f"Expected proposal_two score of 100 but got {proposal_two.score}")
        
        # Verify poll status is not failed (participants met requirements)
        poll.refresh_from_db()
        self.assertNotEqual(poll.status, -1, "Poll should not have failed status")

    def test_delegate_vote_permission_scenarios(self):
        """Test that permission changes actually affect vote count outcomes"""
        # Create a poll with tag
        tag = GroupTagsFactory(group=self.group)
        poll = PollFactory(created_by=self.group_user_creator, poll_type=Poll.PollType.CARDINAL, tag=tag,
                          **generate_poll_phase_kwargs('delegate_vote'))

        # Create proposals for the poll
        proposal_one = PollProposalFactory(created_by=self.group_user_creator, poll=poll)
        proposal_two = PollProposalFactory(created_by=self.group_user_creator, poll=poll)

        # Create a delegate
        delegate = GroupUserDelegateFactory(group=self.group)

        # Test Scenario 1: All delegators with voting permission
        permission_allow_vote = GroupPermissionsFactory(author=self.group, allow_vote=True)

        # Create 3 delegators, all with voting permission
        delegators_with_permission = [
            GroupUserFactory(group=self.group, permission=permission_allow_vote) for _ in range(3)
        ]

        # Create delegator relationships
        delegator_pools = [
            GroupUserDelegatorFactory(group=self.group, delegator=delegator, delegate_pool=delegate.pool)
            for delegator in delegators_with_permission
        ]

        # Add tag to all delegators
        for delegator_pool in delegator_pools:
            delegator_pool.tags.add(tag)

        # Have the delegate vote
        factory = APIRequestFactory()
        user = delegate.group_user.user
        view = PollProposalDelegateVoteUpdateAPI.as_view()
        data = dict(proposals=[proposal_one.id, proposal_two.id], scores=[100, 50])

        request = factory.post('', data)
        force_authenticate(request, user=user)
        response = view(request, poll=poll.id)
        self.assertEqual(response.status_code, 200)

        # Change poll phase to result and call vote count
        Poll.objects.filter(id=poll.id).update(**generate_poll_phase_kwargs('result'))
        poll_proposal_vote_count(poll_id=poll.id)

        # Check mandate with all delegators having permission
        delegate_vote = PollDelegateVoting.objects.get(created_by=delegate.pool, poll=poll)
        self.assertEqual(delegate_vote.mandate, 3, "All 3 delegators should count toward mandate")

        # Check proposal scores
        proposal_one.refresh_from_db()
        proposal_two.refresh_from_db()
        self.assertEqual(proposal_one.score, 300, "Score should be 100 * 3 = 300")
        self.assertEqual(proposal_two.score, 150, "Score should be 50 * 3 = 150")

        # Now test Scenario 2: Change permissions to deny voting for all delegators
        permission_deny_vote = GroupPermissionsFactory(author=self.group, allow_vote=False)

        # Update all delegators to have no voting permission
        for delegator in delegators_with_permission:
            delegator.permission = permission_deny_vote
            delegator.save()

        # Now test Scenario 2: Create a new poll with delegators having no voting permission
        # Create a new poll for the second scenario
        poll_2 = PollFactory(created_by=self.group_user_creator, poll_type=Poll.PollType.CARDINAL, tag=tag,
                            **generate_poll_phase_kwargs('delegate_vote'))

        # Create new proposals for the second poll
        proposal_three = PollProposalFactory(created_by=self.group_user_creator, poll=poll_2)
        proposal_four = PollProposalFactory(created_by=self.group_user_creator, poll=poll_2)

        # Create a new delegate for the second scenario
        delegate_2 = GroupUserDelegateFactory(group=self.group)

        # Create 3 new delegators with no voting permission
        delegators_without_permission = [
            GroupUserFactory(group=self.group, permission=permission_deny_vote) for _ in range(3)
        ]

        # Create delegator relationships for the second delegate
        delegator_pools_2 = [
            GroupUserDelegatorFactory(group=self.group, delegator=delegator, delegate_pool=delegate_2.pool)
            for delegator in delegators_without_permission
        ]

        # Add tag to all delegators in second scenario
        for delegator_pool in delegator_pools_2:
            delegator_pool.tags.add(tag)

        # Have the second delegate vote
        user_2 = delegate_2.group_user.user
        data_2 = dict(proposals=[proposal_three.id, proposal_four.id], scores=[100, 50])

        request_2 = factory.post('', data_2)
        force_authenticate(request_2, user=user_2)
        response_2 = view(request_2, poll=poll_2.id)
        self.assertEqual(response_2.status_code, 200)

        # Change poll phase to result and call vote count for second poll
        Poll.objects.filter(id=poll_2.id).update(**generate_poll_phase_kwargs('result'))
        poll_proposal_vote_count(poll_id=poll_2.id)

        # Check mandate with no delegators having permission
        delegate_vote_2 = PollDelegateVoting.objects.get(created_by=delegate_2.pool, poll=poll_2)
        self.assertEqual(delegate_vote_2.mandate, 0, "No delegators should count toward mandate")

        # Check proposal scores - should be 0 since no delegators have permission
        proposal_three.refresh_from_db()
        proposal_four.refresh_from_db()
        self.assertEqual(proposal_three.score, 0, "Score should be 0 with no voting delegators")
        self.assertEqual(proposal_four.score, 0, "Score should be 0 with no voting delegators")
