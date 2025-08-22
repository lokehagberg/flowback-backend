import json
import random

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate, APITestCase

from flowback.common.tests import generate_request
from flowback.group.models import GroupUser, GroupTags
from flowback.group.tests.factories import GroupFactory, GroupUserFactory, GroupTagsFactory
from flowback.group.views.tag import GroupTagsListApi
from flowback.poll.models import Poll, PollPredictionStatement, PollPredictionStatementSegment, PollPredictionBet, \
    PollPredictionStatementVote
from flowback.poll.services.prediction import update_poll_prediction_statement_outcomes
from flowback.poll.tasks import poll_prediction_bet_count
from flowback.poll.tests.factories import PollFactory, PollPredictionBetFactory, PollProposalFactory, \
    PollPredictionStatementFactory, PollPredictionStatementSegmentFactory, PollPredictionStatementVoteFactory
from flowback.poll.tests.utils import generate_poll_phase_kwargs
from flowback.poll.views.prediction import (PollPredictionStatementCreateAPI,
                                            PollPredictionStatementDeleteAPI,
                                            PollPredictionBetUpdateAPI,
                                            PollPredictionBetDeleteAPI,
                                            PollPredictionStatementVoteCreateAPI,
                                            PollPredictionStatementVoteUpdateAPI,
                                            PollPredictionStatementVoteDeleteAPI,
                                            PollPredictionStatementListAPI,
                                            PollPredictionBetListAPI)


class PollPredictionStatementTest(APITestCase):
    def setUp(self):
        self.group = GroupFactory.create()
        self.user_group_creator = GroupUser.objects.get(group=self.group, user=self.group.created_by)

        (self.user_prediction_creator,
         self.user_prediction_caster_one,
         self.user_prediction_caster_two,
         self.user_prediction_caster_three) = [GroupUserFactory(group=self.group) for _ in range(4)]

        self.poll = PollFactory(created_by=self.user_group_creator,
                                poll_type=4,
                                dynamic=True,
                                tag=GroupTagsFactory(group=self.user_group_creator.group),
                                **generate_poll_phase_kwargs('prediction_statement'))
        (self.proposal_one,
         self.proposal_two,
         self.proposal_three) = [PollProposalFactory(created_by=self.user_group_creator,
                                                     poll=self.poll) for _ in range(3)]
        self.prediction_statement = PollPredictionStatementFactory(created_by=self.user_prediction_creator,
                                                                   poll=self.poll)

        (self.prediction_statement_segment_one,
         self.prediction_statement_segment_two
         ) = [PollPredictionStatementSegmentFactory(prediction_statement=self.prediction_statement,
                                                    proposal=proposal) for proposal in [self.proposal_one,
                                                                                        self.proposal_three]]

    def test_poll_prediction_statement_list(self):
        factory = APIRequestFactory()
        view = PollPredictionStatementListAPI.as_view()

        request = factory.get('', data=dict(proposals=f'{self.proposal_one},{self.proposal_three}'))
        force_authenticate(request, user=self.user_prediction_caster_one.user)
        response = view(request, group_id=self.group.id)
        self.assertEqual(response.status_code, 200, msg=response.data)

        self.assertEqual(self.user_prediction_caster_one.group.id, self.group.id)
        self.assertEqual(self.proposal_one.poll.created_by.group, self.proposal_three.poll.created_by.group)
        self.assertEqual(self.proposal_one.poll.created_by.group, self.user_prediction_caster_one.group)
        self.assertEqual(len(response.data['results']), 1)

    # PredictionBet Statements
    def test_create_prediction_statement(self):
        factory = APIRequestFactory()
        user = self.user_prediction_creator.user
        view = PollPredictionStatementCreateAPI.as_view()

        data = dict(title="Test",
                    description="A Test PredictionBet",
                    end_date=timezone.now() + timezone.timedelta(hours=8),
                    segments=[dict(proposal_id=self.proposal_one.id, is_true=True),
                              dict(proposal_id=self.proposal_two.id, is_true=False)])

        request = factory.post('', data, format='json')
        force_authenticate(request, user=user)
        response = view(request, poll_id=self.poll.id)

        self.assertEqual(response.status_code, 201, msg=response.data)
        prediction_statement = PollPredictionStatement.objects.get(id=int(response.rendered_content))

        total_segments = PollPredictionStatementSegment.objects.filter(prediction_statement=prediction_statement
                                                                       ).count()
        self.assertEqual(total_segments, 2)

    @staticmethod
    def generate_delete_prediction_request(group_user: GroupUser, prediction_statement: PollPredictionStatement):
        factory = APIRequestFactory()
        view = PollPredictionStatementDeleteAPI.as_view()

        request = factory.post('')
        force_authenticate(request, user=group_user.user)
        return view(request, prediction_statement_id=prediction_statement.id)

    def test_delete_prediction_statement(self):
        response = self.generate_delete_prediction_request(group_user=self.user_prediction_creator,
                                                           prediction_statement=self.prediction_statement)
        self.assertEqual(PollPredictionStatement.objects.filter(id=self.prediction_statement.id).count(), 0)

    def test_delete_prediction_statement_unpermitted(self):
        response = self.generate_delete_prediction_request(group_user=self.user_prediction_caster_one,
                                                           prediction_statement=self.prediction_statement)
        data = json.loads(response.rendered_content)

        self.assertEqual(PollPredictionStatement.objects.filter(id=self.prediction_statement.id).count(), 1)

    def test_update_prediction_bet(self):
        Poll.objects.filter(id=self.poll.id).update(**generate_poll_phase_kwargs('prediction_bet'))

        factory = APIRequestFactory()
        view = PollPredictionBetUpdateAPI.as_view()

        (self.prediction_one,
         self.prediction_two,
         self.prediction_three) = [PollPredictionBetFactory(prediction_statement=self.prediction_statement,
                                                            created_by=group_user
                                                            ) for group_user in [self.user_prediction_caster_one,
                                                                                 self.user_prediction_caster_two,
                                                                                 self.user_prediction_caster_three]]

        new_score = self.prediction_one.score
        new_score = random.choice([x for x in range(6) if x != new_score])

        data = dict(score=new_score)

        request = factory.post('', data)
        force_authenticate(request, user=self.user_prediction_caster_one.user)
        response = view(request, prediction_statement_id=self.prediction_one.prediction_statement.id)

        self.assertEqual(response.status_code, 200, msg=response.data)
        score = PollPredictionBet.objects.get(id=self.prediction_one.id).score
        self.assertEqual(score, new_score)

    def test_delete_prediction_bet(self):
        Poll.objects.filter(id=self.poll.id).update(**generate_poll_phase_kwargs('prediction_bet'))

        factory = APIRequestFactory()
        view = PollPredictionBetDeleteAPI.as_view()

        (self.prediction_one,
         self.prediction_two,
         self.prediction_three) = [PollPredictionBetFactory(prediction_statement=self.prediction_statement,
                                                            created_by=group_user
                                                            ) for group_user in [self.user_prediction_caster_one,
                                                                                 self.user_prediction_caster_two,
                                                                                 self.user_prediction_caster_three]]

        request = factory.post('')
        force_authenticate(request, user=self.user_prediction_caster_one.user)
        response = view(request, prediction_statement_id=self.prediction_one.prediction_statement.id)

        self.assertEqual(response.status_code, 200, msg=response.data)
        with self.assertRaises(PollPredictionBet.DoesNotExist):
            PollPredictionBet.objects.get(id=self.prediction_one.id)

    def test_poll_prediction_statement_vote_create(self):
        Poll.objects.filter(id=self.poll.id).update(**generate_poll_phase_kwargs('prediction_vote'))

        factory = APIRequestFactory()
        view = PollPredictionStatementVoteCreateAPI.as_view()

        request = factory.post('', dict(vote=True))
        force_authenticate(request, user=self.user_prediction_caster_one.user)
        response = view(request, prediction_statement_id=self.prediction_statement.id)
        self.assertEqual(response.status_code, 201, msg=response.data)

        prediction = PollPredictionStatementVote.objects.get(created_by=self.user_prediction_caster_one,
                                                             prediction_statement=self.prediction_statement)
        self.assertEqual(prediction.vote, True)

    def test_poll_prediction_statement_vote_update(self):
        Poll.objects.filter(id=self.poll.id).update(**generate_poll_phase_kwargs('prediction_vote'))

        factory = APIRequestFactory()
        view = PollPredictionStatementVoteUpdateAPI.as_view()
        prediction_vote = PollPredictionStatementVoteFactory(prediction_statement=self.prediction_statement,
                                                             created_by=self.user_prediction_caster_one,
                                                             vote=True)

        request = factory.post('', dict(vote=False))
        force_authenticate(request, user=self.user_prediction_caster_one.user)
        response = view(request, prediction_statement_id=prediction_vote.prediction_statement.id)
        self.assertEqual(response.status_code, 200, msg=response.data)

        prediction_vote.refresh_from_db()

        self.assertEqual(prediction_vote.vote, False)

    def test_poll_prediction_statement_vote_delete(self):
        Poll.objects.filter(id=self.poll.id).update(**generate_poll_phase_kwargs('prediction_vote'))

        factory = APIRequestFactory()
        view = PollPredictionStatementVoteDeleteAPI.as_view()
        prediction_vote = PollPredictionStatementVoteFactory(prediction_statement=self.prediction_statement,
                                                             created_by=self.user_prediction_caster_one,
                                                             vote=True)

        request = factory.post('')
        force_authenticate(request, user=self.user_prediction_caster_one.user)
        response = view(request, prediction_statement_id=prediction_vote.prediction_statement.id)
        self.assertEqual(response.status_code, 200, msg=response.data)

        with self.assertRaises(PollPredictionStatementVote.DoesNotExist):
            PollPredictionStatementVote.objects.get(id=prediction_vote.id)

    def test_poll_prediction_list(self):
        Poll.objects.filter(id=self.poll.id).update(**generate_poll_phase_kwargs('prediction_vote'))

        factory = APIRequestFactory()
        view = PollPredictionBetListAPI.as_view()

        (self.prediction_one,
         self.prediction_two,
         self.prediction_three) = [PollPredictionBetFactory(prediction_statement=self.prediction_statement,
                                                            created_by=group_user
                                                            ) for group_user in [self.user_prediction_caster_one,
                                                                                 self.user_prediction_caster_two,
                                                                                 self.user_prediction_caster_three]]

        request = factory.get('')
        force_authenticate(request, user=self.user_prediction_caster_one.user)
        response = view(request, group_id=self.group.id)
        self.assertEqual(response.status_code, 200, msg=response.data)

        self.assertEqual(len(json.loads(response.rendered_content)['results']), 1)

    class BetUser:
        def __init__(self, group_user: GroupUser, score: int, vote: bool):
            self.group_user = group_user
            self.score = score
            self.vote = vote

    @staticmethod
    def generate_previous_bet(poll: Poll, bet_users: list[BetUser]):
        statement = PollPredictionStatementFactory(poll=poll)

        for bet_user in bet_users:
            PollPredictionBetFactory(prediction_statement=statement,
                                     created_by=bet_user.group_user,
                                     score=bet_user.score)
            PollPredictionStatementVoteFactory(prediction_statement=statement,
                                               created_by=bet_user.group_user,
                                               vote=bet_user.vote)

    def run_combined_bet(self, *statements: list[list[int | bool] | None],
                         group_users: list[GroupUser],
                         poll: Poll = None,
                         poll_creator: GroupUser = None,
                         tag: GroupTags = None):
        if not poll:
            poll = PollFactory(created_by=poll_creator or self.user_group_creator,
                               tag=tag or self.poll.tag,
                               **generate_poll_phase_kwargs('prediction_vote'))

        for bets in statements:
            bet_users = []
            for i, bet in enumerate(bets):
                if bet is not None:
                    group_user = GroupUserFactory(group=poll.created_by.group) if not group_users else group_users[i]
                    bet_users.append(self.BetUser(group_user=group_user, score=bet[0], vote=bet[1]))

            self.generate_previous_bet(poll=poll, bet_users=bet_users)

        poll_prediction_bet_count(poll_id=poll.id)

    def test_poll_prediction_combined_bet(self):
        # TODO in future add feature to inject sample values for combined_bets e.g.
        # current_bets = [[0.2, 1.0, 1.0, 0.4, 0.6, 0.8, 0.6, 0.8, 0.6, 0.6, 0.6, 0.2, 0.2, 0.6, 0.2, 1.0]]
        # previous_outcomes = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
        # previous_bets = [[0.2, 0.2, 1.0, 0.6, 0.8, 0.2, 0.2, 1.0, 0.8, 0.6, 0.2, 0.2, 1.0, 0.8, 0.8, 1.0, 1.0, 0.8, 0.2, 0.8, 0.6, 1.0, 0.8, 0.6, 0.8, 0.8, 0.8, 1.0, 0.2, 0.6, 0.2, 0.8, 0.6, 0.6, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.2]]
        # poll_statements = [217, 216, 215, 214, 212, 211, 213, 210, 209, 207, 208, 206, 205, 204, 203, 202]

        # Make random previous bets
        poll_one_bets = [self.BetUser(group_user=self.user_prediction_caster_one,
                                      score=0,
                                      vote=True),
                         self.BetUser(group_user=self.user_prediction_caster_two,
                                      score=1,
                                      vote=True),
                         self.BetUser(group_user=self.user_prediction_caster_three,
                                      score=5,
                                      vote=True)]

        poll = PollFactory(created_by=self.user_group_creator,
                           tag=self.poll.tag,
                           **generate_poll_phase_kwargs('prediction_vote'))
        self.generate_previous_bet(poll=poll, bet_users=poll_one_bets)
        poll_prediction_bet_count(poll_id=poll.id)

        poll_two_bets = [self.BetUser(group_user=self.user_prediction_caster_one,
                                      score=1,
                                      vote=True),
                         self.BetUser(group_user=self.user_prediction_caster_two,
                                      score=0,
                                      vote=True),
                         self.BetUser(group_user=self.user_prediction_caster_three,
                                      score=5,
                                      vote=True)]

        poll_two_bets_two = [self.BetUser(group_user=self.user_prediction_caster_two,
                                          score=0,
                                          vote=True),
                             self.BetUser(group_user=self.user_prediction_caster_three,
                                          score=0,
                                          vote=True),
                             self.BetUser(group_user=self.user_prediction_caster_one,
                                          score=1,
                                          vote=True)]

        poll = PollFactory(created_by=self.user_group_creator,
                           tag=self.poll.tag,
                           **generate_poll_phase_kwargs('prediction_vote'))
        self.generate_previous_bet(poll=poll, bet_users=poll_two_bets)
        self.generate_previous_bet(poll=poll, bet_users=poll_two_bets_two)
        poll_prediction_bet_count(poll_id=poll.id)

        # For irrelevant poll
        poll_three_bets = [self.BetUser(group_user=self.user_prediction_caster_one,
                                        score=0,
                                        vote=True),
                           self.BetUser(group_user=self.user_prediction_caster_two,
                                        score=3,
                                        vote=True),
                           self.BetUser(group_user=self.user_prediction_caster_three,
                                        score=3,
                                        vote=True)]

        poll = PollFactory(created_by=self.user_group_creator,
                           tag=GroupTagsFactory(),
                           **generate_poll_phase_kwargs('prediction_vote'))
        self.generate_previous_bet(poll=poll, bet_users=poll_three_bets)
        poll_prediction_bet_count(poll_id=poll.id)

        self.run_combined_bet([[1, True], [5, True], None],
                              [[3, True], None, [3, False]],
                              [[4, True], [5, True], None],
                              group_users=[self.user_prediction_caster_one,
                                           self.user_prediction_caster_two,
                                           self.user_prediction_caster_three],
                              tag=self.poll.tag)

        # Calculate combined_bet
        (self.prediction_one,
         self.prediction_two,
         self.prediction_three) = [PollPredictionBetFactory(prediction_statement=self.prediction_statement,
                                                            score=0,
                                                            created_by=group_user,
                                                            ) for group_user in [self.user_prediction_caster_one,
                                                                                 self.user_prediction_caster_two,
                                                                                 self.user_prediction_caster_three]]

        poll_prediction_bet_count(poll_id=self.poll.id)
        update_poll_prediction_statement_outcomes(
            poll_prediction_statement_ids=list(PollPredictionStatement.objects.all().values_list('id', flat=True)))

        response = generate_request(api=GroupTagsListApi,
                                    url_params=dict(group_id=self.group),
                                    user=self.user_group_creator.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_poll_prediction_bet_count_edge_cases(self):
        """Test basic edge cases for poll_prediction_bet_count."""
        poll_empty = PollFactory(created_by=self.user_group_creator, tag=self.poll.tag,
                                 **generate_poll_phase_kwargs('prediction_vote'))
        PollPredictionStatementFactory(poll=poll_empty)

        poll_prediction_bet_count(poll_id=poll_empty.id)
        poll_empty.refresh_from_db()
        self.assertEqual(poll_empty.status_prediction, 1)

        poll_single = PollFactory(created_by=self.user_group_creator, tag=self.poll.tag,
                                  **generate_poll_phase_kwargs('prediction_vote'))
        prediction_single = PollPredictionStatementFactory(poll=poll_single)
        PollPredictionBetFactory(prediction_statement=prediction_single,
                                 created_by=self.user_prediction_caster_one, score=2)

        poll_prediction_bet_count(poll_id=poll_single.id)
        poll_single.refresh_from_db()
        self.assertEqual(poll_single.status_prediction, 1)

    def test_poll_prediction_bet_count_multi_user(self):
        """Test poll_prediction_bet_count with multiple users and tags."""

        # Test: Multiple users with different tags
        other_tag = GroupTagsFactory()
        users = [GroupUserFactory(group=self.group) for _ in range(5)]

        # Create historical poll for comparison
        historical_poll = PollFactory(created_by=self.user_group_creator, tag=self.poll.tag,
                                      **generate_poll_phase_kwargs('prediction_vote'))
        historical_statement = PollPredictionStatementFactory(poll=historical_poll)

        # Add votes and bets to historical poll
        PollPredictionStatementVoteFactory(prediction_statement=historical_statement,
                                           created_by=users[0], vote=True)
        for i, user in enumerate(users[:3]):
            PollPredictionBetFactory(prediction_statement=historical_statement,
                                     created_by=user, score=i + 1)

        # Create current poll with multiple users
        current_poll = PollFactory(created_by=self.user_group_creator, tag=self.poll.tag,
                                   **generate_poll_phase_kwargs('prediction_vote'))
        current_statement = PollPredictionStatementFactory(poll=current_poll)

        for i, user in enumerate(users):
            if i < 4:  # Not all users bet
                PollPredictionBetFactory(prediction_statement=current_statement,
                                         created_by=user, score=(i % 5) + 1)

        poll_prediction_bet_count(poll_id=current_poll.id)
        current_poll.refresh_from_db()
        self.assertEqual(current_poll.status_prediction, 1)

    def test_poll_area_vote_count(self):
        """Test poll_area_vote_count task coverage."""
        from flowback.poll.tasks import poll_area_vote_count
        from flowback.poll.models import PollAreaStatement, PollAreaStatementSegment, PollAreaStatementVote

        # Create a poll in area phase
        area_poll = PollFactory(created_by=self.user_group_creator, tag=self.poll.tag,
                                **generate_poll_phase_kwargs('area'))

        # Create area statements with different tags
        tag1 = GroupTagsFactory()
        tag2 = GroupTagsFactory()

        area_statement1 = PollAreaStatement.objects.create(poll=area_poll, created_by=self.user_group_creator)
        area_statement2 = PollAreaStatement.objects.create(poll=area_poll, created_by=self.user_group_creator)

        # Create segments linking statements to tags
        PollAreaStatementSegment.objects.create(poll_area_statement=area_statement1, tag=tag1)
        PollAreaStatementSegment.objects.create(poll_area_statement=area_statement2, tag=tag2)

        # Add votes (more positive votes for statement1)
        for i in range(3):
            user = GroupUserFactory(group=self.group)
            PollAreaStatementVote.objects.create(poll_area_statement=area_statement1, created_by=user, vote=True)

        for i in range(1):
            user = GroupUserFactory(group=self.group)
            PollAreaStatementVote.objects.create(poll_area_statement=area_statement2, created_by=user, vote=True)

        # Test the task
        result = poll_area_vote_count(poll_id=area_poll.id)

        # Verify the poll tag was updated to the winning tag
        area_poll.refresh_from_db()
        self.assertEqual(area_poll.tag, tag1)
        self.assertEqual(result.id, area_poll.id)

        # Test case where no statements exist
        empty_poll = PollFactory(created_by=self.user_group_creator, tag=self.poll.tag,
                                 **generate_poll_phase_kwargs('area'))

        result = poll_area_vote_count(poll_id=empty_poll.id)
        empty_poll.refresh_from_db()
        # Tag should remain unchanged
        self.assertEqual(empty_poll.tag, self.poll.tag)

    def test_poll_prediction_statement_validation_errors(self):
        """Test validation error paths in poll prediction services."""
        from flowback.poll.services.prediction import poll_prediction_statement_create
        from rest_framework.exceptions import ValidationError

        # Test: Empty segments list (line 44)
        with self.assertRaises(ValidationError) as cm:
            poll_prediction_statement_create(
                poll=self.poll.id,
                user=self.user_prediction_caster_one.user,
                title="Test Statement",
                end_date=timezone.now() + timezone.timedelta(days=1),
                segments=[],  # Empty segments should raise error
                description="Test description"
            )
        self.assertIn('atleast one statement', str(cm.exception))

        # Test: Invalid proposal IDs in segments (line 57)
        with self.assertRaises(ValidationError) as cm:
            poll_prediction_statement_create(
                poll=self.poll.id,
                user=self.user_prediction_caster_one.user,
                title="Test Statement",
                end_date=timezone.now() + timezone.timedelta(days=1),
                segments=[{'proposal_id': 999999, 'is_true': True}],  # Invalid proposal ID
                description="Test description"
            )
        self.assertIn('invalid proposal', str(cm.exception))

    def test_poll_prediction_statement_ownership_validation(self):
        """Test ownership validation in prediction statement operations."""
        from flowback.poll.services.prediction import poll_prediction_statement_delete
        from rest_framework.exceptions import ValidationError

        # Create a prediction statement by one user
        statement = PollPredictionStatementFactory(poll=self.poll, created_by=self.user_prediction_caster_one)

        # Try to delete with different user (line 70, 81, 122, 142)
        with self.assertRaises(ValidationError) as cm:
            poll_prediction_statement_delete(
                user=self.user_prediction_caster_two.user,
                prediction_statement_id=statement.id
            )
        self.assertIn('not created by user', str(cm.exception))

    def test_poll_prediction_bet_ownership_validation(self):
        """Test ownership validation in prediction bet operations."""
        from flowback.poll.services.prediction import poll_prediction_bet_delete
        from rest_framework.exceptions import ValidationError

        # Create a prediction bet by one user
        statement = PollPredictionStatementFactory(poll=self.poll)
        bet = PollPredictionBetFactory(prediction_statement=statement,
                                       created_by=self.user_prediction_caster_one, score=3)

        # Try to delete with different user - should raise ValidationError
        with self.assertRaises(ValidationError):
            poll_prediction_bet_delete(
                user=self.user_prediction_caster_two.user,
                prediction_statement_id=statement.id
            )
