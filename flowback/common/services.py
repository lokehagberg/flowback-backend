from typing import List, Dict, Any, Tuple

from rest_framework.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from flowback.common.types import DjangoModelType


def model_update(
    *,
    instance: DjangoModelType,
    fields: List[str],
    data: Dict[str, Any]
) -> Tuple[DjangoModelType, bool]:
    has_updated = False

    for field in fields:
        if field not in data:
            continue

        if getattr(instance, field) != data[field]:
            has_updated = True
            setattr(instance, field, data[field])

    if has_updated:
        instance.full_clean()
        instance.save(update_fields=fields)

    return instance, has_updated


def get_object(model_or_queryset, error_message: str = None, **kwargs):
    try:
        get_object_or_404(model_or_queryset, **kwargs)
    except Http404:
        if not error_message:
            return None
        raise ValidationError(error_message)
