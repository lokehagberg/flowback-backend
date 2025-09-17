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


def get_object(model_or_queryset,
               error_message: str = None,
               reverse: bool = False,
               raise_exception: bool = True,
               **kwargs):
    try:
        data = get_object_or_404(model_or_queryset, **kwargs)
        if reverse:
            if not raise_exception:
                return None
            raise ValidationError(error_message or f'{model_or_queryset._meta.model_name} already exists')

        return data

    except Http404:
        if not raise_exception:
            return None
        if reverse:
            return True
        raise ValidationError(error_message or f'{model_or_queryset._meta.model_name} does not exist')
