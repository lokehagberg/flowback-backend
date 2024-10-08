import django_filters
from django.db.models import OuterRef, Subquery, Sum, Case, When, Q, Count

from flowback.comment.models import Comment, CommentVote
from flowback.user.models import User


class BaseCommentFilter(django_filters.FilterSet):
    order_by = django_filters.OrderingFilter(
        fields=(('created_at', 'created_at_asc'),
                ('-created_at', 'created_at_desc'),
                ('score', 'score_asc'),
                ('-score', 'score_desc')),
        method='order_siblings')

    has_attachments = django_filters.BooleanFilter(method='has_attachments_filter')

    # Orders the tree correctly
    def order_siblings(self, queryset, name, value):
        order_by = [self.filters['order_by'].param_map[x] for x in value]
        return queryset.order_siblings_by(*order_by)

    class Meta:
        model = Comment
        fields = dict(message=['icontains'],
                      author_id=['exact', 'in'],
                      parent_id=['exact'],
                      score=['gt', 'lt'])


# TODO group parents together
def comment_list(*, fetched_by: User, comment_section_id: int, filters=None):
    filters = filters or {}

    user_vote = CommentVote.objects.filter(comment_id=OuterRef('id'), created_by=fetched_by).values('vote')

    if comment_id := filters.get('id'):
        filters.pop('id')
        qs = Comment.objects.get(id=comment_id).descendants(include_self=True).all()

    else:
        qs = Comment.objects.filter(comment_section_id=comment_section_id)

    qs = qs.annotate(user_vote=Subquery(user_vote),
                     raw_score=Count('commentvote', filter=Q(commentvote__vote=True)) -
                               Count('commentvote', filter=Q(commentvote__vote=False))).all()
    return BaseCommentFilter(filters, qs).qs


def comment_ancestor_list(*, fetched_by: User, comment_section_id: int, comment_id: int):
    user_vote = CommentVote.objects.filter(comment_id=OuterRef('id'), created_by=fetched_by).values('vote')

    qs = (Comment.objects.get(comment_section_id=comment_section_id, id=comment_id)
          .ancestors(include_self=True)
          .reverse()
          .annotate(user_vote=Subquery(user_vote),
                    raw_score=Count('commentvote', filter=Q(commentvote__vote=True)) -
                              Count('commentvote', filter=Q(commentvote__vote=False))).all())

    return qs
