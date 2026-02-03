import json

from django.db.models import Sum, Case, When
from rest_framework.test import APITestCase

from flowback.common.tests import generate_request
from flowback.group.models import GroupUser, GroupTags
from flowback.group.tests.factories import GroupFactory, GroupUserFactory, GroupTagsFactory
from flowback.poll.models import Poll, PollAreaStatementSegment, PollAreaStatementVote
from flowback.poll.selectors.area import poll_area_statement_list
from flowback.poll.services.poll import poll_fast_forward
from flowback.poll.tasks import poll_area_vote_count
from flowback.poll.tests.factories import PollFactory
from flowback.poll.tests.utils import generate_poll_phase_kwargs

from flowback.poll.services.area import poll_area_statement_vote_update
from flowback.poll.views.area import PollAreaStatementListAPI


class PollAreaTest(APITestCase):
    def setUp(self):
        self.group = GroupFactory.create()
        self.group_user_creator = self.group.group_user_creator

        (self.group_user_one,
         self.group_user_two,
         self.group_user_three) = [GroupUserFactory(group=self.group) for x in range(3)]

        (self.group_tag_one,
         self.group_tag_two,
         self.group_tag_three) = [GroupTagsFactory(group=self.group) for x in range(3)]

        self.poll = PollFactory(created_by=self.group_user_creator,
                                poll_type=4,
                                **generate_poll_phase_kwargs('area_vote'))

    def test_update_area_vote(self):
        def cast_vote(group_user: GroupUser, poll: Poll, tag_id: int, vote: bool):
            return poll_area_statement_vote_update(user_id=group_user.user.id,
                                                   poll_id=poll.id,
                                                   tag=tag_id,
                                                   vote=vote)

        # Test creating area statements
        area_vote_one = cast_vote(group_user=self.group_user_one,
                                  poll=self.poll,
                                  tag_id=self.group_tag_two.id,
                                  vote=True)

        area_vote_two = cast_vote(group_user=self.group_user_two,
                                  poll=self.poll,
                                  tag_id=self.group_tag_two.id,
                                  vote=True)

        area_vote_three = cast_vote(group_user=self.group_user_three,
                                    poll=self.poll,
                                    tag_id=self.group_tag_one.id,
                                    vote=False)

        self.assertEqual(area_vote_one, area_vote_two)
        self.assertNotEqual(area_vote_one, area_vote_three)

        # Check if segments match properly
        total_area_segments_one = PollAreaStatementSegment.objects.filter(poll_area_statement=area_vote_one,
                                                                          tag_id__in=[self.group_tag_two.id,
                                                                                      self.group_tag_three.id]
                                                                          ).count()
        total_area_segments_two = PollAreaStatementSegment.objects.filter(poll_area_statement=area_vote_one,
                                                                          tag_id__in=[self.group_tag_one.id,
                                                                                      self.group_tag_two.id]
                                                                          ).count()

        self.assertEqual(total_area_segments_one, 1)
        self.assertEqual(total_area_segments_two, 1)

        sum_agg = Sum(Case(When(vote=True, then=1), default=-1))

        def statement_qs(area_statement):
            return PollAreaStatementVote.objects.filter(poll_area_statement=area_statement)

        # Check if votes counted properly
        area_statement_one_votes = statement_qs(area_vote_one).aggregate(result=sum_agg).get('result')
        area_statement_two_votes = statement_qs(area_vote_two).aggregate(result=sum_agg).get('result')
        area_statement_three_votes = statement_qs(area_vote_three).aggregate(result=sum_agg).get('result')

        for qs in [statement_qs(i) for i in [area_vote_one, area_vote_two, area_vote_three]]:
            print([i.vote for i in qs])

        self.assertEqual(area_statement_one_votes, 2)
        self.assertEqual(area_statement_two_votes, 2)
        self.assertEqual(area_statement_three_votes, -1)

        # Check if List API reads properly
        response = generate_request(api=PollAreaStatementListAPI,
                                    user=self.group_user_one.user,
                                    url_params={'poll_id': self.poll.id})

        data = json.loads(response.rendered_content)['results']

        self.assertEqual(len(data), 2)

        # Check if Counting votes work
        winning_tag = GroupTags.objects.filter(pollareastatementsegment__poll_area_statement=area_vote_one).first()
        tag = poll_area_vote_count.apply(kwargs=dict(poll_id=self.poll.id)).get().tag

        self.assertEqual(winning_tag.id, tag.id)

    def test_area_vote_change_then_fast_forward(self):
        """
        Test for the issue where a user votes for one tag, changes their vote to another tag,
        after fast-forwarding the poll, the second tag should be selected.
        
        Scenario:
        1. User votes for tag one
        2. User changes vote to tag two
        3. User fast-forwards the poll
        4. Expected: tag two should be selected
        """
        from flowback.poll.views.area import PollAreaVoteAPI
        from flowback.poll.views.poll import PollListApi

        # Setup a poll in area_vote phase
        poll = PollFactory(created_by=self.group_user_creator,
                           poll_type=4,
                           allow_fast_forward=True,
                           **generate_poll_phase_kwargs('area_vote'))

        user = self.group_user_creator.user

        # First vote: User votes for tag_one
        response1 = generate_request(api=PollAreaVoteAPI,
                                     data={'tag': self.group_tag_one.id, 'vote': True},
                                     user=user,
                                     url_params={'poll_id': poll.id})

        self.assertEqual(response1.status_code, 201, "First vote should succeed")

        # Second vote: User changes mind and votes for tag_two
        response2 = generate_request(api=PollAreaVoteAPI,
                                     data={'tag': self.group_tag_two.id, 'vote': True},
                                     user=user,
                                     url_params={'poll_id': poll.id})

        self.assertEqual(response2.status_code, 201, "Second vote should succeed")

        # Fast forward the poll to complete it
        poll_fast_forward(user_id=user.id, poll_id=poll.id, phase='proposal')
        poll_area_vote_count.apply(kwargs=dict(poll_id=poll.id))

        # Check the poll results via PollListApi
        response3 = generate_request(api=PollListApi,
                                     data={'id': poll.id},
                                     user=user)

        self.assertEqual(response3.status_code, 200, "Poll list should return successfully")

        poll_data = response3.data['results'][0]
        selected_tag_id = poll_data.get('tag_id')

        self.assertEqual(selected_tag_id, self.group_tag_two.id,
                         f"Expected the second vote tag ({self.group_tag_two.id}) to be selected, "
                         f"but got tag ({selected_tag_id}). This demonstrates the bug where the first "
                         f"vote tag is selected instead of the most recent vote.")
