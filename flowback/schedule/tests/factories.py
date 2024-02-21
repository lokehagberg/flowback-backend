import factory
from django.utils import timezone

from flowback.common.tests import fake

from flowback.schedule.models import ScheduleEvent, Schedule


class ScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Schedule

    name = factory.LazyAttribute(lambda _: fake.unique.first_name)


class ScheduleEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduleEvent

    schedule = factory.SubFactory(ScheduleFactory)
    title = factory.LazyAttribute(lambda _: fake.unique.first_name)
    description = factory.LazyAttribute(lambda _: fake.unique.paragraph())
    start_date = factory.LazyAttribute(lambda _: timezone.now())
    end_date = factory.LazyAttribute(lambda _: timezone.now() + timezone.timedelta(hours=1))
