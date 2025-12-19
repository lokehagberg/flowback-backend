import math
import random

import factory

from backend.settings import FLOWBACK_KANBAN_LANES, FLOWBACK_KANBAN_PRIORITY_LIMIT
from flowback.common.tests import fake
from flowback.kanban.models import KanbanEntry, Kanban
from flowback.user.tests.factories import UserFactory


class KanbanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Kanban

    name = factory.lazy_attribute(lambda _: fake.name())
    origin_type = 'test'
    origin_id = factory.lazy_attribute(lambda _: fake.unique.random_int(min=1, max=99999999))


class KanbanEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = KanbanEntry

    title = factory.lazy_attribute(lambda _: fake.name())
    created_by = factory.SubFactory(UserFactory)
    description = factory.lazy_attribute(lambda _: fake.sentence())
    priority = factory.LazyAttribute(lambda _: random.randint(1, math.floor(FLOWBACK_KANBAN_PRIORITY_LIMIT / 2)))
    lane = factory.LazyAttribute(lambda _: random.randint(1, len(FLOWBACK_KANBAN_LANES)))
