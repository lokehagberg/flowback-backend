import random

import factory.django

from flowback.common.tests import fake
from flowback.notification.models import NotificationChannel, NotificationObject


class NotificationChannelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationChannel

    category = factory.LazyAttribute(lambda _: fake.unique.first_name.lower())
    sender_type = "notification"
    sender_id = factory.LazyAttribute(lambda _: random.randint(1, 1000))


class NotificationObjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationObject

    related_id = factory.LazyAttribute(lambda _: random.randint(1, 1000))
    action = factory.LazyAttribute(lambda _: "create")
    message = factory.LazyAttribute(lambda _: fake.description())

