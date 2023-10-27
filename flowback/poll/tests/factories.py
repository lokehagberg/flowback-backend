import factory
from django.utils import timezone
from flowback.common.tests import faker
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


class PollFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Poll

    created_by = factory.SubFactory(GroupUserFactory)
    title = factory.LazyAttribute(lambda _: faker.unique.first_name().lower())
    description = factory.LazyAttribute(lambda _: faker.bs())
    poll_type = factory.LazyAttribute(lambda _: faker.pyint(min_value=1, max_value=4))
    dynamic = factory.LazyAttribute(lambda _: faker.pybool())

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
    
    created_by = factory.SubFactory(GroupUserFactory)
    poll = factory.SubFactory(PollFactory)
    title = factory.LazyAttribute(lambda _: faker.unique.first_name())
    description = factory.LazyAttribute(lambda _: faker.bs())


class PollProposalTypeScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollProposalTypeSchedule

    proposal = factory.SubFactory(PollProposalFactory)
    start_date = factory.LazyAttribute(lambda _: timezone.now())
    end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=1))


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


class PollVotingTypeForAgainstFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollVotingTypeForAgainst

    proposal = factory.SubFactory(PollProposalFactory)


class PollPredictionStatementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollPredictionStatement

    created_by = factory.SubFactory(GroupUserFactory)
    poll = factory.SubFactory(PollFactory, **generate_poll_phase_kwargs('proposal'))
    description = factory.LazyAttribute(lambda _: faker.bs())
    end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=99))


class PollPredictionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollPredictionBet

    prediction_statement = factory.SubFactory(PollPredictionStatementFactory)
    created_by = factory.SubFactory(GroupUserFactory)
    score = factory.LazyAttribute(lambda _: faker.pyint(min_value=0, max_value=5))


class PollPredictionStatementSegmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollPredictionStatementSegment

    prediction_statement = factory.SubFactory(PollPredictionStatementFactory)
    proposal = factory.SubFactory(PollProposalFactory)
    is_true = factory.LazyAttribute(lambda _: faker.pybool())


class PollPredictionStatementVoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PollPredictionStatementVote

    prediction_statement = factory.SubFactory(PollPredictionStatementFactory)
    created_by = factory.SubFactory(GroupUserFactory)
    vote = factory.LazyAttribute(lambda _: faker.pybool())


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
    vote = factory.LazyAttribute(lambda _: faker.pybool())
