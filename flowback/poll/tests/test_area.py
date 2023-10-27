import json

from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase

from flowback.group.models import GroupUser, GroupTags
from flowback.group.tests.factories import GroupFactory, GroupUserFactory, GroupTagsFactory
from flowback.poll.models import Poll, PollAreaStatementSegment, PollAreaStatementVote
from flowback.poll.selectors.area import poll_area_statement_list
from flowback.poll.tasks import poll_area_vote_count
from flowback.poll.tests.factories import PollFactory
from flowback.poll.tests.utils import generate_poll_phase_kwargs

from flowback.poll.services.area import poll_area_statement_vote_update
from flowback.poll.views.area import PollAreaStatementListAPI


class PollAreaTest(APITransactionTestCase):
    reset_sequences = True

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
                                **generate_poll_phase_kwargs('area'))

    def test_update_area_vote(self):
        def vote(group_user: GroupUser, poll: Poll, tags: list[int], vote: bool):
            return poll_area_statement_vote_update(user_id=group_user.user.id,
                                                   poll_id=poll.id,
                                                   tags=tags,
                                                   vote=vote)

        # Test creating area statements
        area_statement_one = vote(group_user=self.group_user_one,
                                  poll=self.poll,
                                  tags=[self.group_tag_two.id, self.group_tag_three.id],
                                  vote=True)

        area_statement_two = vote(group_user=self.group_user_two,
                                  poll=self.poll,
                                  tags=[self.group_tag_two.id, self.group_tag_three.id],
                                  vote=True)

        area_statement_three = vote(group_user=self.group_user_three,
                                    poll=self.poll,
                                    tags=[self.group_tag_one.id, self.group_tag_three.id],
                                    vote=False)

        self.assertEqual(area_statement_one, area_statement_two)
        self.assertNotEqual(area_statement_one, area_statement_three)

        # Check if segments match properly
        total_area_segments_one = PollAreaStatementSegment.objects.filter(poll_area_statement=area_statement_one,
                                                                          tag_id__in=[self.group_tag_two.id,
                                                                                      self.group_tag_three.id]
                                                                          ).count()
        total_area_segments_two = PollAreaStatementSegment.objects.filter(poll_area_statement=area_statement_one,
                                                                          tag_id__in=[self.group_tag_one.id,
                                                                                      self.group_tag_two.id]
                                                                          ).count()

        self.assertEqual(total_area_segments_one, 2)
        self.assertEqual(total_area_segments_two, 1)

        # Check if votes counted properly
        total_votes_one = PollAreaStatementVote.objects.filter(poll_area_statement=area_statement_one, vote=True).count()
        total_votes_two = PollAreaStatementVote.objects.filter(poll_area_statement=area_statement_one, vote=False).count()
        total_votes_three = PollAreaStatementVote.objects.filter(poll_area_statement=area_statement_three).count()

        self.assertEqual(total_votes_one, 2)
        self.assertEqual(total_votes_two, 0)
        self.assertEqual(total_votes_three, 1)

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
        winning_tag = GroupTags.objects.filter(pollareastatementsegment__poll_area_statement=area_statement_one).first()
        tag = poll_area_vote_count.apply(kwargs=dict(poll_id=self.poll.id)).get().tag

        self.assertEqual(winning_tag.name, tag.name)
