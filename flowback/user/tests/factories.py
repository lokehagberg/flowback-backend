import factory
from flowback.common.tests import fake

from flowback.user.models import User, OnboardUser


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.LazyAttribute(lambda _: fake.unique.email())
    username = factory.LazyAttribute(lambda _: fake.unique.first_name().lower())
    password = 'password123abc.!?'


class OnboardUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OnboardUser

    email = factory.LazyAttribute(lambda _: fake.unique.email())
    username = factory.LazyAttribute(lambda _: fake.unique.first_name().lower())


class PasswordResetFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
