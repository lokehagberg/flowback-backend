import django_filters
from typing import Union

from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import Q, Exists, OuterRef, Count, Case, When, F, Subquery, Sum
from django.db.models.functions import Abs
from django.forms import model_to_dict

from flowback.comment.selectors import comment_list, comment_ancestor_list
from flowback.common.filters import NumberInFilter
from flowback.common.services import get_object
from flowback.kanban.selectors import kanban_entry_list
from flowback.poll.models import PollPredictionStatement
from flowback.user.models import User
from flowback.group.models import Group, GroupUser, GroupUserInvite, GroupPermissions, GroupTags, GroupUserDelegator, \
    GroupUserDelegatePool, GroupThread, GroupFolder, GroupThreadVote, WorkGroup, WorkGroupUser, WorkGroupUserJoinRequest
from flowback.schedule.selectors import schedule_event_list
from rest_framework.exceptions import ValidationError, PermissionDenied


def group_default_permissions(*, group: Union[Group, int]):
    if isinstance(group, int):
        group = get_object(Group, id=group)

    if group.default_permission:
        return model_to_dict(group.default_permission)

    fields = GroupPermissions._meta.get_fields()
    fields = [field for field in fields if not field.auto_created
              and field.name not in GroupPermissions.negate_field_perms()]

    defaults = dict()
    for field in fields:
        defaults[field.name] = field.default

    return defaults


# Check if user have any one of the permissions
def group_user_permissions(*,
                           user: Union[User, int] = None,
                           group: Union[Group, int] = None,
                           group_user: GroupUser | int = None,
                           permissions: Union[list[str], str] = None,
                           work_group: WorkGroup | int = None,
                           raise_exception: bool = True,
                           allow_admin: bool = False) -> Union[GroupUser, bool]:
    if isinstance(user, int):
        user = get_object(User, id=user)

    if isinstance(group, int):
        group = get_object(Group, id=group)

    permissions = permissions or []
    admin = False
    work_group_moderator_check = False

    if isinstance(permissions, str):
        permissions = [permissions]

    if user and group:
        group_user = get_object(GroupUser, 'User is not in group', group=group, user=user, active=True)

    elif user and work_group:
        if isinstance(work_group, int):
            work_group = WorkGroup.objects.get(id=work_group)

        group_user = GroupUser.objects.get(group=work_group.group, user=user, active=True)

    elif group_user:
        if isinstance(group_user, int):
            group_user = get_object(GroupUser, id=group_user, active=True)

        elif isinstance(group_user, GroupUser):
            group_user = get_object(GroupUser, id=group_user.id, active=True)

    else:
        raise Exception('group_user_permissions is missing appropiate parameters')

    admin = group_user.is_admin
    perobj = GroupPermissions()
    user_permissions = model_to_dict(group_user.permission) if group_user.permission else group_default_permissions(
        group=group_user.group)

    # Check if admin permission is present
    if 'admin' in permissions:
        if group_user.is_admin or group_user.group.created_by == group_user.user or group_user.user.is_superuser:
            allow_admin = True

        permissions.remove('admin')

    # Check if creator permission is present
    if 'creator' in permissions:
        if group_user.group.created_by == group_user.user or group_user.user.is_superuser:
            allow_admin = True

        permissions.remove('creator')

    # Check if work_group_moderator is present, mark as true and check further down
    if 'work_group_moderator' in permissions:
        work_group_moderator_check = True

        permissions.remove('work_group_moderator')

    validated_permissions = any([user_permissions.get(key, False) for key in permissions]) or not permissions
    if not validated_permissions and not (admin and allow_admin):
        if raise_exception:
            raise PermissionDenied(
                f'Requires one of following permissions: {", ".join(permissions)})')
        else:
            return False

    if work_group and not (admin and allow_admin):
        work_group_user = WorkGroupUser.objects.get(group_user=group_user, work_group=work_group)

        if work_group_moderator_check and not work_group_user.is_moderator:
            raise PermissionDenied("Requires work group moderator permission")

    return group_user


# Simple statement to return Q object for group visibility
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


def group_list(*, fetched_by: User, filters=None):
    filters = filters or {}
    joined_groups = Group.objects.filter(id=OuterRef('pk'), groupuser__user__in=[fetched_by])
    qs = _group_get_visible_for(user=fetched_by
                                ).annotate(joined=Exists(joined_groups),
                                           member_count=Count('groupuser')
                                           ).order_by('created_at').all()
    qs = BaseGroupFilter(filters, qs).qs
    return qs


# TODO uncertain if this feature is used anywhere
def group_folder_list():
    return GroupFolder.objects.all()


def group_kanban_entry_list(*, fetched_by: User, group_id: int, filters=None):
    group_user = group_user_permissions(user=fetched_by, group=group_id)
    subquery = Group.objects.filter(id=OuterRef('kanban__origin_id')).values('name')
    return kanban_entry_list(group_user=group_user,
                             kanban_id=group_user.group.kanban.id,
                             filters=filters,
                             subscriptions=False
                             ).annotate(group_name=Subquery(subquery))


def group_detail(*, fetched_by: User, group_id: int):
    group_user = group_user_permissions(user=fetched_by, group=group_id)
    return Group.objects.annotate(member_count=Count('groupuser')).get(id=group_user.group.id)


def group_schedule_event_list(*, fetched_by: User, group_id: int, filters=None):
    filters = filters or {}
    group_user = group_user_permissions(user=fetched_by, group=group_id)
    return schedule_event_list(schedule_id=group_user.group.schedule.id, group_user=group_user, filters=filters)


class BaseGroupUserFilter(django_filters.FilterSet):
    username__icontains = django_filters.CharFilter(field_name='user__username', lookup_expr='icontains')
    delegate = django_filters.BooleanFilter(field_name='delegate')

    class Meta:
        model = GroupUser
        fields = dict(id=['exact'],
                      user_id=['exact'],
                      is_admin=['exact'],
                      permission=['in'])


def group_user_list(*, group: int, fetched_by: User, filters=None):
    group_user_permissions(user=fetched_by, group=group)
    filters = filters or {}
    is_delegate = GroupUser.objects.filter(group_id=group, groupuserdelegate__group_user=OuterRef('pk'),
                                           groupuserdelegate__group=OuterRef('group')
                                           )
    qs = GroupUser.objects.filter(group_id=group,
                                  active=True
                                  ).annotate(delegate=Exists(is_delegate),
                                             work_groups=ArrayAgg('workgroupuser__work_group__name')).all()
    return BaseGroupUserFilter(filters, qs).qs


class BaseGroupUserDelegatePoolFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter()
    delegate_id = django_filters.NumberFilter(field_name='groupuserdelegate__id')
    group_user_id = django_filters.NumberFilter(field_name='groupuserdelegate__group_user_id')


def group_user_delegate_pool_list(*, group: int, fetched_by: User, filters=None):
    group_user_permissions(user=fetched_by, group=group)
    filters = filters or {}
    qs = GroupUserDelegatePool.objects.filter(group=group).all()
    return BaseGroupUserDelegatePoolFilter(filters, qs).qs


class BaseGroupUserInviteFilter(django_filters.FilterSet):
    username__icontains = django_filters.CharFilter(field_name='user__username', lookup_expr='icontains')

    class Meta:
        model = GroupUserInvite
        fields = ['user', 'group']


def group_user_invite_list(*, group: int, fetched_by: User, filters=None):
    if group:
        group_user_permissions(user=fetched_by, group=group, permissions=['invite_user', 'admin'])
        qs = GroupUserInvite.objects.filter(group_id=group).all()

    else:
        qs = GroupUserInvite.objects.filter(user=fetched_by).all()

    filters = filters or {}
    return BaseGroupUserInviteFilter(filters, qs).qs


class BaseGroupPermissionsFilter(django_filters.FilterSet):
    class Meta:
        model = GroupPermissions
        fields = dict(id=['exact'], role_name=['exact', 'icontains'])


def group_permissions_list(*, group: int, fetched_by: User, filters=None):
    group_user_permissions(user=fetched_by, group=group)
    filters = filters or {}
    qs = GroupPermissions.objects.filter(author_id=group).all()
    return BaseGroupPermissionsFilter(filters, qs).qs


class BaseGroupTagsFilter(django_filters.FilterSet):
    class Meta:
        model = GroupTags
        fields = dict(id=['exact'],
                      name=['exact', 'icontains'],
                      active=['exact'])


def group_tags_list(*, group: int, fetched_by: User, filters=None):
    filters = filters or {}
    group_user_permissions(user=fetched_by, group=group)
    query = Q(group_id=group, active=True)
    if group_user_permissions(user=fetched_by, group=group, permissions=['admin'], raise_exception=False):
        query = Q(group_id=group)

    qs = GroupTags.objects.filter(query).all()
    return BaseGroupTagsFilter(filters, qs).qs


def group_tags_interval_mean_absolute_correctness(*, tag_id: int, fetched_by: User):
    """
    For every combined_bet & outcome in a given tag:
        abs(sum(combined_bet) – sum(outcome))/N
        - N is the number of predictions that had at least one bet

    TODO add this value to the group_tags_list selector
    """
    tag = GroupTags.objects.get(id=tag_id)
    group_user_permissions(user=fetched_by, group=tag.group)

    qs_filter = PollPredictionStatement.objects.filter(poll__tag_id=tag_id, pollpredictionstatementvote__isnull=False)

    qs_annotate = qs_filter.annotate(
        outcome_sum=Sum(Case(When(pollpredictionstatementvote__vote=True, then=1),
                             When(pollpredictionstatementvote__vote=False, then=-1),
                             default=0,
                             output_field=models.IntegerField())),

        outcome=Case(When(outcome_sum__gt=0, then=1),
                     When(outcome_sum__lte=0, then=0),
                     default=0.5,
                     output_field=models.DecimalField(max_digits=14, decimal_places=4)),
        has_bets=Case(When(pollpredictionbet__isnull=True, then=0), default=1),
        p1=Abs(F('combined_bet') - F('outcome')))

    qs = qs_annotate.aggregate(interval_mean_absolute_correctness=1 - (Sum('p1') / Sum('has_bets')))
    return qs.get('interval_mean_absolute_correctness')


class BaseGroupUserDelegateFilter(django_filters.FilterSet):
    delegate_id = django_filters.NumberFilter()
    delegate_user_id = django_filters.NumberFilter(field_name='delegate__user_id')
    delegate_name__icontains = django_filters.CharFilter(field_name='delegate__user__username__icontains')
    tag_id = django_filters.NumberFilter(field_name='tags__id')
    tag_name = django_filters.CharFilter(field_name='tags__name')
    tag_name__icontains = django_filters.CharFilter(field_name='tags__tag_name', lookup_expr='icontains')

    class Meta:
        model = GroupUserDelegator
        fields = ['delegate_id']


def group_user_delegate_list(*, group: int, fetched_by: User, filters=None):
    filters = filters or {}
    fetched_by = group_user_permissions(user=fetched_by, group=group)
    query = Q(group_id=group, delegator_id=fetched_by)

    qs = GroupUserDelegator.objects.filter(query).all()
    return BaseGroupUserDelegateFilter(filters, qs).qs


class BaseGroupThreadFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(
        fields=(('created_at', 'created_at_asc'),
                ('-created_at', 'created_at_desc'),
                ('pinned', 'pinned')))
    user_vote = django_filters.BooleanFilter()
    id_list = NumberInFilter(field_name='id')

    class Meta:
        model = GroupThread
        fields = dict(id=['exact'],
                      title=['icontains'],
                      description=['icontains'])


def group_thread_list(*, group_id: int, fetched_by: User, filters=None):
    filters = filters or {}
    group_user = group_user_permissions(user=fetched_by, group=group_id)

    sq_user_vote = GroupThreadVote.objects.filter(thread_id=OuterRef('id'), created_by=group_user).values('vote')

    qs = (GroupThread.objects.filter(created_by__group_id=group_id)
          .annotate(total_comments=Count('comment_section__comment',
                                         filter=Q(comment_section__comment__active=True)),
                    user_vote=Subquery(sq_user_vote),
                    score=Count('groupthreadvote', filter=Q(groupthreadvote__vote=True)) -
                          Count('groupthreadvote', filter=Q(groupthreadvote__vote=False))).all())

    return BaseGroupThreadFilter(filters, qs).qs


def group_thread_comment_list(*, fetched_by: User, thread_id: int, filters=None):
    thread = get_object(GroupThread, id=thread_id)
    group_user_permissions(user=fetched_by, group=thread.created_by.group)

    return comment_list(fetched_by=fetched_by, comment_section_id=thread.comment_section_id, filters=filters)


def group_thread_comment_ancestor_list(*, fetched_by: User, thread_id: int, comment_id: int):
    thread = get_object(GroupThread, id=thread_id)
    group_user_permissions(user=fetched_by, group=thread.created_by.group)

    return comment_ancestor_list(fetched_by=fetched_by,
                                 comment_section_id=thread.comment_section.id,
                                 comment_id=comment_id)


def group_delegate_pool_comment_list(*, fetched_by: User, delegate_pool_id: int, filters=None):
    filters = filters or {}
    delegate_pool = get_object(GroupUserDelegatePool, id=delegate_pool_id)
    group_user_permissions(user=fetched_by, group=delegate_pool.group)

    return comment_list(fetched_by=fetched_by, comment_section_id=delegate_pool.comment_section.id, filters=filters)


# Work Group
class BaseWorkGroupFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc'),
                                                     ('name', 'name_asc'),
                                                     ('-name', 'name_desc'))
                                             )
    joined = django_filters.BooleanFilter()

    class Meta:
        model = WorkGroup
        fields = dict(id=['exact'],
                      name=['exact', 'icontains'])


def work_group_list(*, group_id: int, fetched_by: User, filters=None):
    filters = filters or {}
    group_user = group_user_permissions(user=fetched_by, group=group_id)

    qs = WorkGroup.objects.filter(group_id=group_id
                                  ).annotate(joined=Q(workgroupuser__group_user__in=[group_user]),
                                             member_count=Count('workgroupuser'))

    return BaseWorkGroupFilter(filters, qs).qs


# Work Group User
class BaseWorkGroupUserFilter(django_filters.FilterSet):
    user_id = django_filters.CharFilter(field_name='group_user__user_id', lookup_expr='exact')
    username = django_filters.CharFilter(field_name='group_user__user__username', lookup_expr='icontains')

    class Meta:
        model = WorkGroupUser
        fields = dict(id=['exact'],
                      group_user_id=['exact'])


def work_group_user_list(*, work_group_id: int, fetched_by: User, filters=None):
    filters = filters or {}

    # Won't need to check group_user_permission if the user is already in the work group
    group_user = group_user_permissions(user=fetched_by, work_group=work_group_id, allow_admin=True)

    qs = WorkGroupUser.objects.filter(work_group_id=work_group_id
                                      ).annotate(joined=Q(group_user__in=[group_user]))

    return BaseWorkGroupFilter(filters, qs).qs


# Work Group User
class BaseWorkGroupUserJoinRequestFilter(django_filters.FilterSet):
    user_id = django_filters.CharFilter(field_name='group_user__user_id', lookup_expr='exact')
    group_user_id = django_filters.CharFilter(lookup_expr='exact')

    username = django_filters.CharFilter(field_name='group_user__user__username', lookup_expr='icontains')

    class Meta:
        model = WorkGroupUserJoinRequest
        fields = dict(id=['exact'],
                      group_user_id=['exact'])


def work_group_user_join_request_list(*, work_group_id: int, fetched_by: User, filters=None):
    filters = filters or {}

    work_group = WorkGroup.objects.get(id=work_group_id)

    # Won't need to check if group_user is in work_group due to admin/moderator requirement
    group_user_is_admin = group_user_permissions(user=fetched_by, group=work_group.group, permissions=['admin'])
    work_group_user_is_moderator = WorkGroupUser.objects.filter(id=work_group_id,
                                                                group_user__user__in=[fetched_by],
                                                                is_moderator=True).exists()

    if group_user_is_admin or work_group_user_is_moderator:
        qs = WorkGroupUserJoinRequest.objects.filter(id=work_group_id)

        return BaseWorkGroupFilter(filters, qs).qs

    return PermissionDenied()
