from django.db import models
from django.utils import timezone
from pgtrigger import Q


class BaseModel(models.Model):
    created_at = models.DateTimeField(db_index=True, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# Generates a query where only one of the fields is allowed to be set, while all other fields must be null
def generate_exclusive_q(fields: list[str]) -> Q:
    queryset_merge = None

    for i in range(len(fields)):
        queryset_slice = None

        for j, field in enumerate(fields):
            queryset_slice &= Q(**{field: i == j})

        queryset_merge |= queryset_slice

    return Q(queryset_merge)
