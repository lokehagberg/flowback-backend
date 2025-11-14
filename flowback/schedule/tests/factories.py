import factory
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta

from flowback.common.tests import fake
from flowback.schedule.models import (Schedule, ScheduleTag, ScheduleEvent,
                                      ScheduleUser, ScheduleEventSubscription,
                                      ScheduleTagSubscription)
from flowback.group.tests.factories import GroupFactory, GroupUserFactory
from flowback.user.tests.factories import UserFactory


class ScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Schedule

    @factory.lazy_attribute
    def content_type(self):
        group = GroupFactory.create()
        self.object_id = group.id
        return ContentType.objects.get_for_model(group)

    @factory.lazy_attribute
    def object_id(self):
        # This will be set by content_type lazy attribute
        return getattr(self, '_object_id', 1)

    @object_id.setter
    def object_id(self, value):
        self._object_id = value

    active = True


class ScheduleTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduleTag

    schedule = factory.SubFactory(ScheduleFactory)
    name = factory.LazyAttribute(lambda _: fake.word())


class ScheduleEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduleEvent

    schedule = factory.SubFactory(ScheduleFactory)
    title = factory.LazyAttribute(lambda _: fake.sentence(nb_words=5))
    description = factory.LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    start_date = factory.LazyAttribute(lambda _: timezone.now() + timedelta(days=1))
    end_date = factory.LazyAttribute(lambda o: o.start_date + timedelta(hours=2))
    active = True
    tag = factory.SubFactory(ScheduleTagFactory, schedule=factory.SelfAttribute('..schedule'))

    @factory.lazy_attribute
    def content_type(self):
        group = GroupFactory.create()
        self.object_id = group.id
        return ContentType.objects.get_for_model(group)

    @factory.lazy_attribute
    def object_id(self):
        return getattr(self, '_object_id', 1)

    @object_id.setter
    def object_id(self, value):
        self._object_id = value

    meeting_link = factory.LazyAttribute(lambda _: fake.url())
    repeat_frequency = None


class ScheduleUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduleUser

    user = factory.SubFactory(UserFactory)
    schedule = factory.SubFactory(ScheduleFactory)
    subscribe_to_new_notification_tags = False
    reminders = None


class ScheduleEventSubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduleEventSubscription

    event = factory.SubFactory(ScheduleEventFactory)
    schedule_user = factory.SubFactory(ScheduleUserFactory, schedule=factory.SelfAttribute('..event.schedule'))
    reminders = None
    tags = None
    locked = True


class ScheduleTagSubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduleTagSubscription

    schedule_user = factory.SubFactory(ScheduleUserFactory)
    schedule_tag = factory.SubFactory(ScheduleTagFactory, schedule=factory.SelfAttribute('..schedule_user.schedule'))
    reminders = None
