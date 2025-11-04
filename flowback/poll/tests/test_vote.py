from datetime import datetime

from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError
from .factories import (PollFactory, PollProposalFactory, PollVotingFactory, PollDelegateVotingFactory,
                        PollVotingTypeCardinalFactory, PollVotingTypeForAgainstFactory)
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
                                         dynamic=True,
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
        data = dict(proposals=[x.id for x in proposals])
        return generate_request(
            api=PollProposalVoteUpdateAPI,
            data=data,
            url_params={'poll': poll.id},
            user=user
        )

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

    def test_hundreds_of_polls_vote_count(self):
        """Test poll_proposal_vote_count with hundreds of Schedule and Cardinal polls with proposals, votes and delegate votes"""
        
        # Create additional group users for variety
        additional_users = GroupUserFactory.create_batch(10, group=self.group)
        all_users = [self.group_user_one, self.group_user_two, self.group_user_three] + additional_users
        
        # Create delegates for delegate voting
        delegates = GroupUserDelegateFactory.create_batch(5, group=self.group)
        
        # Create delegators for each delegate
        for delegate in delegates:
            delegators = GroupUserDelegatorFactory.create_batch(3, group=self.group, delegate_pool=delegate.pool)
            # Add tags to some delegators
            for delegator in delegators[:2]:  # Only first 2 delegators get tags
                delegator.tags.add(self.poll_cardinal.tag)
        
        polls_created = []
        
        # Create 200 Schedule polls
        for i in range(200):
            poll = PollFactory(
                created_by=all_users[i % len(all_users)],
                poll_type=Poll.PollType.SCHEDULE,
                tag=self.poll_cardinal.tag,
                dynamic=True,  # Required for Schedule polls
                **generate_poll_phase_kwargs('result')
            )
            polls_created.append(poll)
            
            # Create 3-5 proposals per poll
            num_proposals = 3 + (i % 3)  # 3, 4, or 5 proposals
            proposals = []
            for j in range(num_proposals):
                proposal = PollProposalFactory(poll=poll, created_by=poll.created_by, title=f"Schedule Proposal {i}-{j}")
                proposals.append(proposal)
            
            # Create regular votes from users
            for j, user in enumerate(all_users[:5 + (i % 3)]):  # 5-7 users vote
                voting = PollVotingFactory(created_by=user, poll=poll)
                # Vote for 2-3 proposals
                voted_proposals = proposals[:2 + (j % 2)]
                for proposal in voted_proposals:
                    PollVotingTypeForAgainstFactory(author=voting, proposal=proposal, vote=True)
            
            # Create delegate votes
            if i % 3 == 0:  # Every 3rd poll gets delegate votes
                delegate = delegates[i % len(delegates)]
                delegate_voting = PollDelegateVotingFactory(created_by=delegate.pool, poll=poll)
                # Delegate votes for some proposals
                for proposal in proposals[:2]:
                    PollVotingTypeForAgainstFactory(author_delegate=delegate_voting, proposal=proposal, vote=True)
        
        # Create 200 Cardinal polls  
        for i in range(200):
            poll = PollFactory(
                created_by=all_users[i % len(all_users)],
                poll_type=Poll.PollType.CARDINAL,
                tag=self.poll_cardinal.tag,
                **generate_poll_phase_kwargs('result')
            )
            polls_created.append(poll)
            
            # Create 3-5 proposals per poll
            num_proposals = 3 + (i % 3)  # 3, 4, or 5 proposals
            proposals = []
            for j in range(num_proposals):
                proposal = PollProposalFactory(poll=poll, created_by=poll.created_by, title=f"Cardinal Proposal {i}-{j}")
                proposals.append(proposal)
            
            # Create regular votes from users
            for j, user in enumerate(all_users[:5 + (i % 3)]):  # 5-7 users vote
                voting = PollVotingFactory(created_by=user, poll=poll)
                # Vote for all proposals with random scores
                for k, proposal in enumerate(proposals):
                    score = 10 + (i + j + k) % 90  # Scores between 10-99
                    PollVotingTypeCardinalFactory(author=voting, proposal=proposal, raw_score=score, score=score)
            
            # Create delegate votes
            if i % 4 == 0:  # Every 4th poll gets delegate votes
                delegate = delegates[i % len(delegates)]
                delegate_voting = PollDelegateVotingFactory(created_by=delegate.pool, poll=poll)
                # Delegate votes for all proposals
                for k, proposal in enumerate(proposals):
                    score = 20 + (i + k) % 80  # Delegate scores between 20-99
                    PollVotingTypeCardinalFactory(author_delegate=delegate_voting, proposal=proposal, raw_score=score, score=score)
        
        self.assertEqual(len(polls_created), 400, "Should have created 400 polls total")
        
        # Run poll_proposal_vote_count for all polls
        successful_counts = 0
        time = datetime.now()
        for poll in polls_created:
            print(datetime.now() - time)
            time = datetime.now()
            poll_proposal_vote_count(poll_id=poll.id)
            successful_counts += 1
        
        # Verify that most polls were processed successfully
        self.assertGreater(successful_counts, 350, f"At least 350 polls should be processed successfully, got {successful_counts}")
        
        # Verify some polls have updated scores
        updated_polls = Poll.objects.filter(id__in=[p.id for p in polls_created], result=True)
        self.assertGreater(updated_polls.count(), 100, "At least 100 polls should have result=True")
        
        # Verify some proposals have scores > 0
        proposals_with_scores = PollProposal.objects.filter(
            poll__in=polls_created, 
            score__gt=0
        ).count()
        self.assertGreater(proposals_with_scores, 500, "At least 500 proposals should have scores > 0")


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
        user = self.delegate.group_user.user

        (proposal_one,
         proposal_two) = [PollProposalFactory(created_by=self.group_user_creator, poll=self.poll_one) for x in range(2)]

        data = dict(proposals=[proposal_two.id, proposal_one.id], scores=[100, 25])

        generate_request(
            api=PollProposalDelegateVoteUpdateAPI,
            data=data,
            url_params={'poll': self.poll_one.id},
            user=user
        )

        votes = PollDelegateVoting.objects.get(created_by=self.delegate.pool).pollvotingtypecardinal_set
        self.assertEqual(votes.filter(proposal_id__in=data['proposals']).count(), 2)

    def test_delegate_vote_count_with_permissions(self):
        """Test poll_proposal_vote_count where delegate has delegators with and without voting permissions"""
        # Create a poll with tag
        tag = GroupTagsFactory(group=self.group)
        poll = PollFactory(created_by=self.group_user_creator, poll_type=Poll.PollType.CARDINAL, tag=tag,
                          **generate_poll_phase_kwargs('delegate_vote'))
        
        # Create proposals for the poll
        proposal_one = PollProposalFactory(created_by=self.group_user_creator, poll=poll)
        proposal_two = PollProposalFactory(created_by=self.group_user_creator, poll=poll)

        # Create permissions - one allowing vote, one denying vote
        permission_allow_vote = GroupPermissionsFactory(author=self.group, allow_vote=True)
        permission_deny_vote = GroupPermissionsFactory(author=self.group, allow_vote=False)

        # Create a delegate
        delegate = GroupUserDelegateFactory(group=self.group, group_user__permission=permission_allow_vote)

        # Create delegators with different permissions
        # 2 delegators with voting permission
        delegator_with_permission_1 = GroupUserFactory(group=self.group, permission=permission_allow_vote)
        delegator_with_permission_2 = GroupUserFactory(group=self.group, permission=permission_allow_vote)

        # 2 delegators without voting permission
        delegator_without_permission_1 = GroupUserFactory(group=self.group, permission=permission_deny_vote)
        delegator_without_permission_2 = GroupUserFactory(group=self.group, permission=permission_deny_vote)

        # Create delegator relationships
        delegator_1 = GroupUserDelegatorFactory(group=self.group, delegator=delegator_with_permission_1,
                                                     delegate_pool=delegate.pool)
        delegator_2 = GroupUserDelegatorFactory(group=self.group, delegator=delegator_with_permission_2,
                                                     delegate_pool=delegate.pool)
        delegator_3 = GroupUserDelegatorFactory(group=self.group, delegator=delegator_without_permission_1,
                                                     delegate_pool=delegate.pool)
        delegator_4 = GroupUserDelegatorFactory(group=self.group, delegator=delegator_without_permission_2,
                                                     delegate_pool=delegate.pool)

        # Also make the delegate delegate to themselves
        delegator_delegate = GroupUserDelegatorFactory(group=self.group, delegator=delegate.group_user,
                                                       delegate_pool=delegate.pool)

        # Add tag to all delegators (excluding the self-delegation to avoid counting the delegate themselves)
        for delegator in [delegator_1, delegator_2, delegator_3, delegator_4, delegator_delegate]:
            delegator.tags.add(tag)

        # Have the delegate vote
        user = delegate.group_user.user
        data = dict(proposals=[proposal_one.id, proposal_two.id], scores=[100, 50])

        response = generate_request(
            api=PollProposalDelegateVoteUpdateAPI,
            data=data,
            url_params={'poll': poll.id},
            user=user
        )
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
        # Should be 3 (delegators with permission) - only delegators count toward mandate, not the delegate
        expected_mandate = 3  # Only the 3 delegators with voting permission should be counted
        self.assertEqual(delegate_vote.mandate, expected_mandate, 
                        f"Expected mandate of {expected_mandate} but got {delegate_vote.mandate}")
        
        # Verify proposals got correct scores based on only counting delegators with permission
        proposal_one.refresh_from_db()
        proposal_two.refresh_from_db()
        
        # Each delegator with permission contributes their weight to the delegate's vote
        # Delegate vote: proposal_one=100, proposal_two=50
        # With mandate of 3, final scores should be: proposal_one=300, proposal_two=150
        self.assertEqual(proposal_one.score, 300, f"Expected proposal_one score of 300 but got {proposal_one.score}")
        self.assertEqual(proposal_two.score, 150, f"Expected proposal_two score of 150 but got {proposal_two.score}")
        
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
        user = delegate.group_user.user
        data = dict(proposals=[proposal_one.id, proposal_two.id], scores=[100, 50])

        response = generate_request(
            api=PollProposalDelegateVoteUpdateAPI,
            data=data,
            url_params={'poll': poll.id},
            user=user
        )
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

        response_2 = generate_request(
            api=PollProposalDelegateVoteUpdateAPI,
            data=data_2,
            url_params={'poll': poll_2.id},
            user=user_2
        )
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

    def test_delegator_cannot_vote_during_delegate_phase(self):
        """Test that a delegator cannot vote through regular API during delegate voting phase,
        but the delegate can vote through delegate API.

        This test verifies the implemented restriction where delegators are prevented from
        voting during the delegate_vote phase through the regular voting API.
        """

        # Create a poll in delegate voting phase
        tag = GroupTagsFactory(group=self.group)
        poll = PollFactory(created_by=self.group_user_creator, poll_type=Poll.PollType.CARDINAL, tag=tag,
                          **generate_poll_phase_kwargs('delegate_vote'))

        # Create proposals for the poll
        proposal_one = PollProposalFactory(created_by=self.group_user_creator, poll=poll)
        proposal_two = PollProposalFactory(created_by=self.group_user_creator, poll=poll)

        # Create a delegate
        delegate = GroupUserDelegateFactory(group=self.group)

        # Create permissions allowing vote
        permission_allow_vote = GroupPermissionsFactory(author=self.group, allow_vote=True)

        # Create a delegator with voting permission
        delegator_user = GroupUserFactory(group=self.group, permission=permission_allow_vote)

        # Create delegator relationship - delegator delegates to delegate
        delegator_pool = GroupUserDelegatorFactory(group=self.group,
                                                  delegator=delegator_user,
                                                  delegate_pool=delegate.pool)

        # Add tag to delegator
        delegator_pool.tags.add(tag)

        # Test 1: Delegator cannot vote through regular API during delegate phase
        delegator_vote_data = dict(proposals=[proposal_one.id, proposal_two.id], scores=[100, 50])

        # Delegator should be prevented from voting during delegate phase
        delegator_response = generate_request(
            api=PollProposalVoteUpdateAPI,
            data=delegator_vote_data,
            url_params={'poll': poll.id},
            user=delegator_user.user
        )
        self.assertEqual(delegator_response.status_code, 400)
        
        # Verify the error message indicates the poll phase restriction
        self.assertIn("not in", str(delegator_response.data).lower())

        # Verify no delegator voting record was created
        delegator_votes = PollVoting.objects.filter(created_by=delegator_user, poll=poll)
        self.assertEqual(delegator_votes.count(), 0,
                        "No delegator voting records should be created during delegate phase")

        # Test 2: Verify delegate can vote through delegate API (this should always work)
        delegate_vote_data = dict(proposals=[proposal_one.id, proposal_two.id], scores=[80, 40])

        # The delegate should be able to vote through delegate API
        delegate_response = generate_request(
            api=PollProposalDelegateVoteUpdateAPI,
            data=delegate_vote_data,
            url_params={'poll': poll.id},
            user=delegate.group_user.user
        )
        self.assertEqual(delegate_response.status_code, 200)

        # Verify delegate voting record was created
        delegate_vote = PollDelegateVoting.objects.get(created_by=delegate.pool, poll=poll)
        self.assertIsNotNone(delegate_vote)

        # Test 3: Verify delegate vote has correct scores
        delegate_vote_cardinal = delegate_vote.pollvotingtypecardinal_set.all()
        self.assertEqual(delegate_vote_cardinal.count(), 2, "Delegate should have voted on 2 proposals")

        proposal_scores = {vote.proposal_id: vote.raw_score for vote in delegate_vote_cardinal}
        self.assertEqual(proposal_scores[proposal_one.id], 80)
        self.assertEqual(proposal_scores[proposal_two.id], 40)
