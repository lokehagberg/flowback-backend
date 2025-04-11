import factory
from factory import post_generation

from flowback.common.tests import fake

from ..models import CommentSection, Comment, CommentVote
from ...user.tests.factories import UserFactory


class CommentSectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CommentSection


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    comment_section = factory.SubFactory(CommentSectionFactory)
    author = factory.SubFactory(UserFactory)
    message = factory.LazyAttribute(lambda _: fake.paragraph())

    @factory.post_generation
    def post(self, create, extracted, **kwargs):
        if score := kwargs.get('score'):
            self.score = score
            self.save()


class CommentVoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CommentVote

    comment = factory.SubFactory(CommentFactory)
    created_by = factory.SubFactory(UserFactory)
    vote = factory.LazyAttribute(lambda _: fake.boolean())
