import django_filters
from django.db import models
from django.db.models import OuterRef, Q, Exists, Subquery, F
from django_filters import FilterSet
from rest_framework.exceptions import ValidationError

from flowback.common.filters import NumberInFilter
from flowback.group.models import Group, GroupUser, GroupThread, GroupThreadVote
from flowback.poll.models import Poll, PollVoting
from flowback.kanban.selectors import kanban_entry_list
from flowback.user.models import User, UserChatInvite
from backend.settings import env


class UserFilter(FilterSet):
    class Meta:
        model = User
        fields = {'id': ['exact'],
                  'username': ['exact', 'icontains']
                  }


def get_user(fetched_by: User, user_id: int = None):
    def user_to_dict(u, fields):
        return {field: getattr(user, field, None) for field in fields}

    if user_id:
        user = User.objects.get(id=user_id)

    else:
        user = fetched_by

    share_groups = User.objects.filter(group__groupuser__user__in=[fetched_by, user]).exists()

    if fetched_by == user:
        return user

    elif (user.public_status == User.PublicStatus.PUBLIC
          or (share_groups and user.public_status == User.PublicStatus.GROUP_ONLY)):
        return user_to_dict(user, ('id', 'username',
                                   'profile_image', 'banner_image',
                                   'public_status', 'chat_status',
                                   'bio', 'website', 'contact_email', 'contact_phone',
                                   'public_status'))

    else:
        return user_to_dict(user, ('id', 'username', 'profile_image',
                                   'banner_image', 'public_status', 'chat_status'))


def user_kanban_entry_list(*, fetched_by: User, filters=None):
    filters = filters or {}
    return kanban_entry_list(kanban_id=fetched_by.kanban.id, filters=filters, subscriptions=True)


def user_list(*, fetched_by: User, filters=None):
    # Block access to this api for members, unless group admin or higher.
    if env('FLOWBACK_GROUP_ADMIN_USER_LIST_ACCESS_ONLY') \
            and not Group.objects.filter(created_by=fetched_by).exists() \
            and not GroupUser.objects.filter(user=fetched_by, is_admin=True) \
            and not (fetched_by.is_staff and fetched_by.is_superuser):
        raise ValidationError('User must be group admin or higher')

    filters = filters or {}
    qs = User.objects.all()
    return UserFilter(filters, qs).qs


class UserHomeFeedFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(fields=(('created_at', 'created_at_asc'),
                                                     ('-created_at', 'created_at_desc'),
                                                     ('-pinned', 'pinned')))
    id = django_filters.NumberFilter(lookup_expr='exact')
    created_by_id = django_filters.NumberFilter(lookup_expr='exact')
    work_group_ids = NumberInFilter()
    title__icontains = django_filters.CharFilter(lookup_expr='icontains')
    description = django_filters.CharFilter(lookup_expr='icontains')
    created_at__gt = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gt')
    created_at__lt = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lt')
    related_model = django_filters.CharFilter(lookup_expr='exact')
    group_joined = django_filters.BooleanFilter(lookup_expr='exact')
    user_vote = django_filters.BooleanFilter(lookup_expr='exact')
    pinned = django_filters.BooleanFilter(lookup_expr='exact')
    group_ids = NumberInFilter(field_name='created_by__group_id')


# TODO add relevant Count (proposal, prediction, comments) to the home feed if possible
def user_home_feed(*, fetched_by: User, filters=None):
    filters = filters or {}
    ordering_filter = {}

    if 'order_by' in filters.keys():
        ordering_filter['order_by'] = filters.pop('order_by')

    joined_groups = Group.objects.filter(id=OuterRef('created_by__group_id'), groupuser__user__in=[fetched_by])
    related_fields = ['id',
                      'created_by',
                      'created_at',
                      'updated_at',
                      'group_id',
                      'work_group_id',
                      'title',
                      'description',
                      'related_model',
                      'group_joined',
                      'user_vote',
                      'pinned']

    q = (Q(created_by__group__groupuser__user__in=[fetched_by])
         & Q(created_by__group__groupuser__active=True))  # User in group

    thread_qs = GroupThread.objects.filter(
        Q(created_by__group__public=True)
        & ~Q(created_by__group__groupuser__user__in=[fetched_by])  # Group is Public
        & Q(work_group__isnull=True)
        & Q(public=True)

        | q & Q(created_by__group__public=True)
        & Q(created_by__group__groupuser__user__in=[fetched_by])
        & Q(created_by__group__groupuser__active=False)  # User in group but not active, and group is public
        & Q(work_group__isnull=True)
        & Q(public=True)

        | q & Q(work_group__isnull=True)  # All threads without workgroup

        | q & Q(work_group__isnull=False)  # User in workgroup
        & Q(work_group__workgroupuser__group_user__user=fetched_by)

        | q & Q(work_group__isnull=False)  # User is admin in group
        & Q(created_by__group__groupuser__user=fetched_by)
        & Q(created_by__group__groupuser__is_admin=True))

    group_thread_vote = GroupThreadVote.objects.filter(thread_id=OuterRef('id'),
                                                       created_by__user=fetched_by).values('vote')
    thread_qs = thread_qs.annotate(related_model=models.Value('thread', models.CharField()),
                                   group_id=F('created_by__group_id'),
                                   group_joined=Exists(joined_groups),
                                   user_vote=Subquery(group_thread_vote))
    thread_qs = thread_qs.values(*related_fields)
    thread_qs = UserHomeFeedFilter(filters, thread_qs).qs


    # Poll
    poll_qs = Poll.objects.filter(
        q & Q(work_group__isnull=True)  # User in Group

        | Q(created_by__group__public=True)
        & ~Q(created_by__group__groupuser__user__in=[fetched_by])  # Group is Public
        & Q(work_group__isnull=True)
        & Q(public=True)

        | q & Q(work_group__isnull=False)  # User in workgroup
        & Q(work_group__workgroupuser__group_user__user=fetched_by)

        | q & Q(created_by__group__public=True)
        & Q(created_by__group__groupuser__user__in=[fetched_by])
        & Q(created_by__group__groupuser__active=False)  # User in group but not active, and group is public
        & Q(work_group__isnull=True)
        & Q(public=True)

        | q & Q(work_group__isnull=False)  # User is admin in group
        & Q(created_by__group__groupuser__user=fetched_by)
        & ~Q(created_by__group__groupuser__user__in=[fetched_by])
        & Q(created_by__group__groupuser__is_admin=True))

    poll_user_vote = PollVoting.objects.filter(poll_id=OuterRef('id'), created_by__user=fetched_by)
    poll_qs = poll_qs.annotate(related_model=models.Value('poll', models.CharField()),
                               group_id=F('created_by__group_id'),
                               group_joined=Exists(joined_groups),
                               user_vote=Exists(poll_user_vote))
    poll_qs = poll_qs.values(*related_fields)
    poll_qs = UserHomeFeedFilter(filters, poll_qs).qs

    qs = thread_qs.union(poll_qs).order_by('-created_at')
    qs = UserHomeFeedFilter(ordering_filter, qs).qs

    return qs


class UserChatInviteFilter(django_filters.FilterSet):
    user_id = django_filters.NumberFilter(field_name="user_id", lookup_expr="exact")
    message_channel_id = django_filters.NumberFilter(field_name="message_channel_id", lookup_expr="exact")
    rejected = django_filters.BooleanFilter(field_name="rejected", lookup_expr="exact")
    rejected__isnull = django_filters.BooleanFilter(field_name="rejected", lookup_expr="isnull")

    class Meta:
        model = UserChatInvite
        fields = ['user_id', 'message_channel_id', 'rejected', 'rejected__isnull']


def user_chat_invite_list(*, fetched_by: User, filters=None):
    filters = filters or {}

    qs = UserChatInvite.objects.filter(user=fetched_by).all()

    return UserChatInviteFilter(filters, qs).qs
