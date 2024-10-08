import random

import factory

from flowback.common.tests import fake
from flowback.kanban.models import KanbanEntry


class KanbanFactory(factory.Factory):
    class Meta:
        model = KanbanEntry

    name = factory.lazy_attribute(lambda _: fake.name())
    origin_type = 'test'
    origin_id = factory.lazy_attribute(lambda _: fake.unique.random_int(min=1, max=99999999))


class KanbanEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = KanbanEntry

    description = factory.lazy_attribute(lambda _: fake.sentence())
    tag = factory.LazyAttribute(lambda _: random.randint(1, 5))
