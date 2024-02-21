import factory
from flowback.common.tests import fake

from ..models import (Message,
                      MessageChannel,
                      MessageChannelParticipant,
                      MessageFileCollection,
                      MessageChannelTopic)
from flowback.user.tests.factories import UserFactory
from ...files.tests.factories import FileCollectionFactory


class MessageChannelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MessageChannel

    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=2))
    origin_name = "message"


class MessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Message

    user = factory.SubFactory(UserFactory)
    channel = factory.SubFactory(MessageChannelFactory)
    message = factory.LazyAttribute(lambda _: fake.sentence())


class MessageChannelParticipantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MessageChannelParticipant

    user = factory.SubFactory(UserFactory)
    channel = factory.SubFactory(MessageChannelFactory)


class MessageChannelTopicFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MessageChannelTopic

    channel = factory.SubFactory(MessageChannelFactory)
    name = factory.LazyAttribute(lambda _: fake.name())


class MessageFileCollectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MessageFileCollection

    user = factory.SubFactory(UserFactory)
    channel = factory.SubFactory(MessageChannelFactory)
    file_collection = factory.SubFactory(FileCollectionFactory)
