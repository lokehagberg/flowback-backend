import django_filters

from flowback.group.models import GroupUserDelegatePool
from flowback.group.selectors.permission import group_user_permissions
from flowback.user.models import User


class BaseGroupUserDelegatePoolFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter()
    delegate_id = django_filters.NumberFilter(field_name='groupuserdelegate__id')
    group_user_id = django_filters.NumberFilter(field_name='groupuserdelegate__group_user_id')


def group_user_delegate_pool_list(*, group: int, fetched_by: User, filters=None):
    group_user_permissions(user=fetched_by, group=group)
    filters = filters or {}
    qs = GroupUserDelegatePool.objects.filter(group=group).all()
    return BaseGroupUserDelegatePoolFilter(filters, qs).qs
