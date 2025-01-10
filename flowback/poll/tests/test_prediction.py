import json
import random
from pprint import pprint

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.db.models import Sum, Case, When, F
from django.db.models.functions import Abs
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate, APITransactionTestCase

from flowback.group.models import GroupUser
from flowback.group.tests.factories import GroupFactory, GroupUserFactory, GroupTagsFactory
from flowback.group.views.tag import GroupTagsListApi, GroupTagIntervalMeanAbsoluteCorrectnessAPI
from flowback.poll.models import Poll, PollPredictionStatement, PollPredictionStatementSegment, PollPredictionBet, \
    PollPredictionStatementVote
from flowback.poll.tasks import poll_prediction_bet_count
from flowback.poll.tests.factories import PollFactory, PollPredictionBetFactory, PollProposalFactory, \
    PollPredictionStatementFactory, PollPredictionStatementSegmentFactory, PollPredictionStatementVoteFactory
from flowback.poll.tests.utils import generate_poll_phase_kwargs

from flowback.poll.views.prediction import (PollPredictionStatementCreateAPI,
                                            PollPredictionStatementDeleteAPI,
                                            PollPredictionBetCreateAPI,
                                            PollPredictionBetUpdateAPI,
                                            PollPredictionBetDeleteAPI,
                                            PollPredictionStatementVoteCreateAPI,
                                            PollPredictionStatementVoteUpdateAPI,
                                            PollPredictionStatementVoteDeleteAPI,
                                            PollPredictionStatementListAPI,
                                            PollPredictionBetListAPI)


class PollPredictionStatementTest(APITransactionTestCase):
    def setUp(self):
        # Group Preparation
        self.group = GroupFactory.create()
        self.user_group_creator = GroupUserFactory(group=self.group, user=self.group.created_by)

        (self.user_prediction_creator,
         self.user_prediction_caster_one,
         self.user_prediction_caster_two,
         self.user_prediction_caster_three) = [GroupUserFactory(group=self.group) for x in range(4)]

        # Poll Preparation
        self.poll = PollFactory(created_by=self.user_group_creator,
                                poll_type=4,
                                dynamic=True,
                                tag=GroupTagsFactory(group=self.user_group_creator.group),
                                **generate_poll_phase_kwargs('prediction_statement'))
        (self.proposal_one,
         self.proposal_two,
         self.proposal_three) = [PollProposalFactory(created_by=self.user_group_creator,
                                                     poll=self.poll) for x in range(3)]
        # Predictions Preparation
        self.prediction_statement = PollPredictionStatementFactory(created_by=self.user_prediction_creator,
                                                                   poll=self.poll)

        (self.prediction_statement_segment_one,
         self.prediction_statement_segment_two
         ) = [PollPredictionStatementSegmentFactory(prediction_statement=self.prediction_statement,
                                                    proposal=proposal) for proposal in [self.proposal_one,
                                                                                        self.proposal_three]]

    # PredictionBet Statements
    def test_create_prediction_statement(self):
        factory = APIRequestFactory()
        user = self.user_prediction_creator.user
        view = PollPredictionStatementCreateAPI.as_view()

        data = dict(title="Test",
                    description="A Test PredictionBet",
                    end_date=timezone.now() + timezone.timedelta(hours=8),
                    segments=[dict(proposal_id=self.proposal_one.id, is_true=True),
                              dict(proposal_id=self.proposal_two.id, is_true=False)],
                    attachments=[SimpleUploadedFile('something_one.txt',
                                                    f'test?'.encode(), content_type='text/plain'),
                                 SimpleUploadedFile('something_two.txt',
                                                    f'test_two?'.encode(), content_type='text/plain')])

        request = factory.post('', data, format='json')
        force_authenticate(request, user=user)
        response = view(request, poll_id=self.poll.id)

        self.assertEqual(response.status_code, 201, msg=response.data)
        prediction_statement = PollPredictionStatement.objects.get(id=int(response.rendered_content))

        total_segments = PollPredictionStatementSegment.objects.filter(prediction_statement=prediction_statement
                                                                       ).count()
        self.assertEqual(total_segments, 2,
                         f"Segment(s) not created, 2 expected, {total_segments} created.")

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
        self.assertEqual(PollPredictionStatement.objects.filter(id=self.prediction_statement.id).count(),
                         0, 'Deletion failed.')

    def test_delete_prediction_statement_unpermitted(self):
        response = self.generate_delete_prediction_request(group_user=self.user_prediction_caster_one,
                                                           prediction_statement=self.prediction_statement)
        data = json.loads(response.rendered_content)

        self.assertEqual(PollPredictionStatement.objects.filter(id=self.prediction_statement.id).count(),
                         1, 'Possibly passed with unpermitted user.')

    # Predictions
    def test_create_prediction_bet(self):
        Poll.objects.filter(id=self.poll.id).update(**generate_poll_phase_kwargs('prediction_bet'))

        factory = APIRequestFactory()
        view = PollPredictionBetCreateAPI.as_view()

        data = dict(score=5)

        request = factory.post('', data)
        force_authenticate(request, user=self.user_prediction_caster_one.user)
        response = view(request, prediction_statement_id=self.prediction_statement.id)

        self.assertEqual(response.status_code, 201, msg=response.data)
        bets = PollPredictionBet.objects.filter(created_by=self.user_prediction_caster_one,
                                                prediction_statement_id=self.prediction_statement.id)

        self.assertEqual(bets.count(), 1, "PredictionBet not created")

        self.assertEqual(bets.first().score, 5, "PredictionBet not matching input score")

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
        self.assertEqual(score, new_score, f"Score '{score}' is not matching the new score {new_score}.")

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
        with self.assertRaises(PollPredictionBet.DoesNotExist, msg='PredictionBet not removed.'):
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
        self.assertEqual(prediction.vote, True, 'Vote isnt same as requested by user')

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

        self.assertEqual(prediction_vote.vote, False, 'Vote isnt same as requested by user')

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

        with self.assertRaises(PollPredictionStatementVote.DoesNotExist, msg='Prediction Vote not removed.'):
            PollPredictionStatementVote.objects.get(id=prediction_vote.id)

    def test_poll_prediction_statement_list(self):
        factory = APIRequestFactory()
        view = PollPredictionStatementListAPI.as_view()

        request = factory.get('', data=dict(proposals='1,3'))
        force_authenticate(request, user=self.user_prediction_caster_one.user)
        response = view(request, group_id=self.group.id)
        self.assertEqual(response.status_code, 200, msg=response.data)

        self.assertEqual(len(json.loads(response.rendered_content)['results']), 1,
                         'Incorrect amount of prediction statements returned')

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

        self.assertEqual(len(json.loads(response.rendered_content)['results']), 1,
                         'Incorrect amount of predictions returned')

    class BetUser:
        def __init__(self, group_user: GroupUser, score: int, vote: bool):
            self.group_user = group_user
            self.score = score
            self.vote = vote

        group_user: GroupUser
        score: int  # between 0 and 5
        vote: bool

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

    def test_poll_prediction_combined_bet(self):
        # Make random previous bets
        poll_one_bets = [self.BetUser(group_user=self.user_prediction_caster_one,
                                      score=0,
                                      vote=True),
                         self.BetUser(group_user=self.user_prediction_caster_two,
                                      score=0,
                                      vote=True),
                         self.BetUser(group_user=self.user_prediction_caster_three,
                                      score=0,
                                      vote=True)]

        poll = PollFactory(created_by=self.user_group_creator,
                           tag=self.poll.tag,
                           **generate_poll_phase_kwargs('prediction_vote'))
        self.generate_previous_bet(poll=poll, bet_users=poll_one_bets)
        poll_prediction_bet_count(poll_id=poll.id)

        poll_two_bets = [self.BetUser(group_user=self.user_prediction_caster_one,
                                      score=0,
                                      vote=True),
                         self.BetUser(group_user=self.user_prediction_caster_two,
                                      score=0,
                                      vote=True),
                         self.BetUser(group_user=self.user_prediction_caster_three,
                                      score=0,
                                      vote=True)]

        poll = PollFactory(created_by=self.user_group_creator,
                           tag=self.poll.tag,
                           **generate_poll_phase_kwargs('prediction_vote'))
        self.generate_previous_bet(poll=poll, bet_users=poll_two_bets)
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
        print(self.poll.tag, self.prediction_statement.combined_bet)
        print([i.combined_bet for i in PollPredictionStatement.objects.all()])

        # Query Test
        qs = PollPredictionStatement.objects.filter(poll__tag=self.poll.tag, pollpredictionstatementvote__isnull=False)

        qs_outcome = qs.annotate(
            outcome_sum=Sum(Case(When(pollpredictionstatementvote__vote=True, then=1),
                                 When(pollpredictionstatementvote__vote=False, then=-1),
                                 default=0,
                                 output_field=models.IntegerField())),

            outcome=Case(When(outcome_sum__gt=0, then=1),
                         When(outcome_sum__lte=0, then=0),
                         default=0.5,
                         output_field=models.DecimalField(max_digits=14, decimal_places=4)),
            has_bets=Case(When(pollpredictionbet__isnull=True, then=0), default=1),
            p1=Abs(F('combined_bet') - F('outcome')))

        pprint([i.__dict__ for i in qs_outcome])
        print(qs_outcome.aggregate(interval_mean_absolute_error=(Sum('p1') / Sum('has_bets'))))

        # Request Test
        factory = APIRequestFactory()
        user = self.user_group_creator.user
        view = GroupTagIntervalMeanAbsoluteCorrectnessAPI.as_view()

        request = factory.get('', data=dict(limit=10))
        force_authenticate(request, user=user)
        response = view(request, tag_id=self.poll.tag_id)

        data = json.loads(response.rendered_content)
        pprint(data)
