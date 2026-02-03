import random

import factory.django

from flowback.common.tests import fake
from flowback.group.tests.factories import GroupFactory
from flowback.user.tests.factories import UserFactory
from flowback.notification.models import (
    NotificationChannel, 
    NotificationObject, 
    Notification, 
    NotificationSubscription,
    NotificationSubscriptionTag
)


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


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    user = factory.SubFactory(UserFactory)
    notification_object = factory.SubFactory(NotificationObjectFactory)
    reminder = 0
    read = False


class NotificationSubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationSubscription

    user = factory.SubFactory(UserFactory)
    channel = factory.SubFactory(NotificationChannelFactory)


class NotificationSubscriptionTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationSubscriptionTag

    subscription = factory.SubFactory(NotificationSubscriptionFactory)
    name = factory.LazyAttribute(lambda _: fake.word())
    reminders = factory.LazyAttribute(lambda _: [300, 600, 3600])

