from typing import Union

import django_filters

from flowback.common.services import get_object
from flowback.kanban.models import KanbanEntry
from flowback.user.models import User
from flowback.group.selectors import group_user_permissions


class BaseKanbanEntryFilter(django_filters.FilterSet):
    group_id = django_filters.NumberFilter(field_name='created_by__group_id')
    created_by = django_filters.NumberFilter(field_name='created_by__user_id')
    assignee = django_filters.NumberFilter(field_name='assignee__user_id')

    class Meta:
        model = KanbanEntry
        fields = dict(title=['icontains'],
                      description=['icontains'],
                      tag=['exact'],
                      )


def kanban_list(*, fetched_by: User, group_id: Union[int, None], filters=None):
    filters = filters or {}

    if group_id:
        user = group_user_permissions(group=group_id, user=fetched_by)
        qs = KanbanEntry.objects.filter(created_by__group=user.group).all()

    else:
        qs = KanbanEntry.objects.filter(created_by__group__groupuser__user__in=[fetched_by]).all()

    return BaseKanbanEntryFilter(filters, qs).qs
