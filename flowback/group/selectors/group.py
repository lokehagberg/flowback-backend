import django_filters
from django.db.models import OuterRef, Exists, Count, Q

from flowback.group.models import Group, GroupFolder
from flowback.group.selectors.permission import group_user_permissions
from flowback.user.models import User


def group_list(*, fetched_by: User, filters=None):
    filters = filters or {}
    joined_groups = Group.objects.filter(id=OuterRef('pk'), groupuser__user__in=[fetched_by], groupuser__active=True)
    pending_join = Group.objects.filter(id=OuterRef('pk'),
                                        groupuserinvite__user__in=[fetched_by],
                                        groupuserinvite__external=True)
    pending_invite = Group.objects.filter(id=OuterRef('pk'),
                                          groupuserinvite__user__in=[fetched_by],
                                          groupuserinvite__external=False)

    qs = _group_get_visible_for(user=fetched_by
                                ).annotate(joined=Exists(joined_groups),
                                           pending_invite=Exists(pending_invite),
                                           pending_join=Exists(pending_join),
                                           member_count=Count('groupuser')
                                           ).order_by('created_at').all()
    qs = BaseGroupFilter(filters, qs).qs
    return qs


def _group_get_visible_for(user: User):
    query = Q(public=True) | Q(Q(public=False) & Q(groupuser__user__in=[user]))
    return Group.objects.filter(query)


class BaseGroupFilter(django_filters.FilterSet):
    joined = django_filters.BooleanFilter(lookup_expr='exact')
    chat_ids = django_filters.NumberFilter(lookup_expr='in')
    exclude_folders = django_filters.BooleanFilter(lookup_expr='isnull')

    class Meta:
        model = Group
        fields = dict(id=['exact'],
                      name=['exact', 'icontains'],
                      direct_join=['exact'],
                      group_folder_id=['exact'])


def group_folder_list():
    return GroupFolder.objects.all()


def group_detail(*, fetched_by: User, group_id: int):
    group_user = group_user_permissions(user=fetched_by, group=group_id)
    return Group.objects.annotate(member_count=Count('groupuser')).get(id=group_user.group.id)
