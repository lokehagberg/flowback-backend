import django_filters
from django.db.models import Q

from flowback.common.filters import NumberInFilter
from flowback.group.models import WorkGroupUser, Group
from flowback.kanban.models import KanbanEntry
from flowback.user.models import User


class BaseKanbanEntryFilter(django_filters.FilterSet):
    origin_type = django_filters.CharFilter(field_name='kanban__origin_type')
    origin_id = django_filters.NumberFilter(field_name='kanban__origin_id')
    created_by = django_filters.NumberFilter()
    work_group_ids = NumberInFilter(field_name='work_group_id')
    order_by = django_filters.OrderingFilter(fields=(('priority', 'priority_asc'),
                                                     ('-priority', 'priority_desc')))
    assignee = django_filters.NumberFilter()

    class Meta:
        model = KanbanEntry
        fields = dict(title=['exact', 'icontains'],
                      description=['exact', 'icontains'],
                      end_date=['gt', 'lt'],
                      lane=['exact', 'icontains'])


# TODO due for rework
def kanban_entry_list(*, user: User, filters=None):
    filters = filters or {}
    qs = KanbanEntry.objects.filter(Q(Q(kanban__origin_type="user") & Q(kanban__origin_id=user.id)) |
                                    Q(Q(kanban__group__active=True)
                                      & Q(kanban__group__groupuser__user=user)
                                      & Q(kanban__group__groupuser__active=True)),
                                    active=True
                                    ).exclude(Q(work_group__isnull=False)
                                              & ~Q(work_group__workgroupuser__group_user__user=user)
                                              & Q(work_group__workgroupuser__active=True))

    return BaseKanbanEntryFilter(filters, qs).qs
