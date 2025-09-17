import random

import factory.django

from flowback.common.tests import fake
from flowback.group.tests.factories import GroupFactory
from flowback.notification.models import NotificationChannel, NotificationObject


class NotificationChannelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationChannel

    content_object = factory.SubFactory(GroupFactory)


class NotificationObjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationObject

    action = factory.LazyAttribute(lambda _: "CREATED")
    message = factory.LazyAttribute(lambda _: fake.sentence())
    channel = factory.SubFactory(NotificationChannelFactory)

