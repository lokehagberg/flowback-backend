import json

from django.db.models import Sum, Case, When
from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase

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
        self.group_user_creator = GroupUserFactory(group=self.group, user=self.group.created_by)

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
        factory = APIRequestFactory()
        user = self.group_user_one.user
        view = PollAreaStatementListAPI.as_view()

        request = factory.get('', format='json')
        force_authenticate(request, user)
        response = view(request, poll_id=self.poll.id)

        data = json.loads(response.rendered_content)['results']

        self.assertEqual(len(data), 2)

        # Check if Counting votes work
        winning_tag = GroupTags.objects.filter(pollareastatementsegment__poll_area_statement=area_vote_one).first()
        tag = poll_area_vote_count.apply(kwargs=dict(poll_id=self.poll.id)).get().tag

        self.assertEqual(winning_tag.id, tag.id)
