import django_filters
from django.db import models
from django.db.models import Q, Subquery, OuterRef, Count
from django.db.models.functions import Coalesce

from flowback.comment.models import Comment
from flowback.comment.selectors import comment_list, comment_ancestor_list
from flowback.common.filters import NumberInFilter
from flowback.common.services import get_object
from flowback.group.models import GroupThread, GroupThreadVote
from flowback.group.selectors.permission import group_user_permissions
from flowback.user.models import User


class BaseGroupThreadFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(
        fields=(('created_at', 'created_at_asc'),
                ('-created_at', 'created_at_desc'),
                ('-pinned', 'pinned')))
    user_vote = django_filters.BooleanFilter()
    id_list = NumberInFilter(field_name='id')
    group_ids = NumberInFilter(field_name='created_by__group_id')
    work_group_ids = NumberInFilter(field_name='work_group_id')

    class Meta:
        model = GroupThread
        fields = dict(id=['exact'],
                      title=['exact', 'icontains'],
                      description=['icontains'])


def group_thread_list(*, fetched_by: User, filters=None):
    filters = filters or {}

    threads = GroupThread.objects.filter(
        Q(Q(work_group__isnull=True)  # All threads without workgroup
          | Q(work_group__isnull=False) & Q(  # All threads with workgroup
            Q(work_group__workgroupuser__group_user__user=fetched_by))  # Check if groupuser is member in workgroup
          | Q(Q(created_by__group__groupuser__user=fetched_by) & Q(
            created_by__group__groupuser__is_admin=True)))  # Check if groupuser is admin in group
    ).values('id')

    threads = GroupThread.objects.filter(id__in=[t['id'] for t in threads])  # TODO make this one query

    comment_qs = Coalesce(Subquery(
        Comment.objects.filter(comment_section_id=OuterRef('comment_section_id'), active=True).values(
            'comment_section_id').annotate(total=Count('*')).values('total')[:1]), 0)

    user_vote_qs = GroupThreadVote.objects.filter(thread_id=OuterRef('id'), created_by__user=fetched_by).values('vote')

    positive_votes_qs = (
        GroupThreadVote.objects.filter(
            thread_id=OuterRef('pk'),
            vote=True
        )
        .values('thread_id')
        .annotate(positive_count=Count('id'))
        .values('positive_count')
    )

    negative_votes_qs = (
        GroupThreadVote.objects.filter(
            thread_id=OuterRef('pk'),
            vote=False
        )
        .values('thread_id')
        .annotate(negative_count=Count('id'))
        .values('negative_count')
    )

    qs = threads.annotate(total_comments=comment_qs,
                          user_vote=Subquery(user_vote_qs),
                          score=Coalesce(Subquery(positive_votes_qs,
                                                  output_field=models.IntegerField()), 0) -
                                Coalesce(Subquery(negative_votes_qs,
                                                  output_field=models.IntegerField()), 0)).all()

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
