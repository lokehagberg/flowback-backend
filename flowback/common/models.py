from django.db import models
from django.db.models import When, Case
from django.utils import timezone
from pgtrigger import Q


class BaseModel(models.Model):
    created_at = models.DateTimeField(db_index=True, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# Generates a query where only one of the fields is allowed to be set, while all other fields must be null
def generate_exclusive_q(*fields: str) -> Q:
    queryset_merge = None

    for i in range(len(fields)):
        queryset_slice = None

        for j, field in enumerate(fields):
            queryset_slice &= Q(**{field: i == j})

        queryset_merge |= queryset_slice

    return Q(queryset_merge)


def generate_exclusive_constraint_eq(*, base: str, target: str, fields: tuple) -> Case:
    """
    Generates Case of exclusive constraint query for given fields, allows for checking if e.g. user is in the
    same group as other fields
    :type base: str, the base route to the exclusive model reference
    :type target: str, the absolute route to the target to compare
    :type fields: tuple[tuple[str, str]], list of fields for each exclusive constraint, appended with the base field.
                  First value is to check if it's null, second is to check if it's equal to the target
    """
    constraints = []
    for exist_field, compare_field in fields:
        constraints.append(When(Q(**{f"{base}__{exist_field}": False}),
                                then=Q(**{f"{base}__{compare_field}": compare_field})))

    return Case(*constraints, default=False)
