import factory
from django.utils import timezone
from flowback.common.tests import fake
from flowback.group.tests.factories import GroupUserFactory, GroupUserDelegatePoolFactory, GroupTagsFactory

from flowback.poll.models import (Poll,
                                  PollProposal,
                                  PollProposalTypeSchedule,
                                  PollVoting,
                                  PollDelegateVoting,
                                  PollVotingTypeRanking,
                                  PollVotingTypeCardinal,
                                  PollVotingTypeForAgainst,
                                  PollPredictionBet,
                                  PollPredictionStatement,
                                  PollPredictionStatementSegment,
                                  PollPredictionStatementVote,
                                  PollAreaStatement,
                                  PollAreaStatementSegment,
                                  PollAreaStatementVote)
from flowback.poll.tests.utils import generate_poll_phase_kwargs
from flowback.schedule.tests.factories import ScheduleEventFactory


class PollFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Poll

    created_by = factory.SubFactory(GroupUserFactory)
    title = factory.LazyAttribute(lambda _: fake.unique.first_name().lower())
    description = factory.LazyAttribute(lambda _: fake.bs())
    poll_type = 4
    dynamic = False

    start_date = factory.LazyAttribute(lambda _: timezone.now())
    area_vote_end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=1))
    proposal_end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=2))
    prediction_statement_end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=3))
    prediction_bet_end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=4))
    delegate_vote_end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=5))
    vote_end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=6))
    end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=7))


class PollProposalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollProposal

    @factory.post_generation
    def generate_schedule_event(obj, create, extracted, **kwargs):
        if not create:
            return

        if obj.poll.poll_type == Poll.PollType.SCHEDULE:
            PollProposalTypeScheduleFactory(proposal=obj, **kwargs)
    
    created_by = factory.SubFactory(GroupUserFactory)
    poll = factory.SubFactory(PollFactory)
    title = factory.LazyAttribute(lambda _: fake.unique.first_name())
    description = factory.LazyAttribute(lambda _: fake.bs())


class PollProposalTypeScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollProposalTypeSchedule

    proposal = factory.SubFactory(PollProposalFactory, poll__poll_type=3)
    event = factory.SubFactory(ScheduleEventFactory,
                               schedule=factory.SelfAttribute('..proposal.poll.polltypeschedule.schedule'),
                               origin_id=factory.SelfAttribute('..proposal.id'),
                               origin_name=factory.SelfAttribute('..proposal.schedule_origin'))


class PollVotingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollVoting

    created_by = factory.SubFactory(GroupUserFactory)
    poll = factory.SubFactory(PollFactory)


class PollDelegateVotingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollDelegateVoting

    created_by = factory.SubFactory(GroupUserDelegatePoolFactory)
    poll = factory.SubFactory(PollFactory)


class PollVotingTypeRankingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollVotingTypeRanking

    proposal = factory.SubFactory(PollProposalFactory)


class PollVotingTypeCardinalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollVotingTypeCardinal

    proposal = factory.SubFactory(PollProposalFactory)
    score = factory.LazyAttribute(lambda _: fake.pyint())


class PollVotingTypeForAgainstFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollVotingTypeForAgainst

    proposal = factory.SubFactory(PollProposalFactory)


class PollPredictionStatementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollPredictionStatement

    created_by = factory.SubFactory(GroupUserFactory)
    poll = factory.SubFactory(PollFactory, **generate_poll_phase_kwargs('proposal'))
    title = factory.LazyAttribute(lambda _: fake.name())
    description = factory.LazyAttribute(lambda _: fake.bs())
    end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=99))


class PollPredictionBetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollPredictionBet

    prediction_statement = factory.SubFactory(PollPredictionStatementFactory)
    created_by = factory.SubFactory(GroupUserFactory)
    score = factory.LazyAttribute(lambda _: fake.pyint(min_value=0, max_value=5))


class PollPredictionStatementSegmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollPredictionStatementSegment

    prediction_statement = factory.SubFactory(PollPredictionStatementFactory)
    proposal = factory.SubFactory(PollProposalFactory)
    is_true = factory.LazyAttribute(lambda _: fake.pybool())


class PollPredictionStatementVoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollPredictionStatementVote

    prediction_statement = factory.SubFactory(PollPredictionStatementFactory)
    created_by = factory.SubFactory(GroupUserFactory)
    vote = factory.LazyAttribute(lambda _: fake.pybool())


class PollAreaStatementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollAreaStatement

    created_by = factory.SubFactory(GroupUserFactory)
    poll = factory.SubFactory(PollFactory, **generate_poll_phase_kwargs('area'))


class PollAreaStatementSegmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollAreaStatementSegment

    poll_area_statement = factory.SubFactory(PollAreaStatementFactory)
    tag = factory.SubFactory(GroupTagsFactory)


class PollAreaStatementVoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollAreaStatementVote

    created_by = factory.SubFactory(GroupUserFactory)
    poll_area_statement = factory.SubFactory(PollAreaStatementFactory)
    vote = factory.LazyAttribute(lambda _: fake.pybool())
