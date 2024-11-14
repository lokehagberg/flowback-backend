from math import sqrt

from django.db import models
from django.db.models import Q, Count
from django.db.models.signals import post_save, post_delete
from tree_queries.models import TreeNode

from flowback.common.models import BaseModel


class CommentSection(BaseModel):
    active = models.BooleanField(default=True)


class Comment(BaseModel, TreeNode):
    comment_section = models.ForeignKey(CommentSection, on_delete=models.CASCADE)
    author = models.ForeignKey("user.User", on_delete=models.CASCADE)
    message = models.TextField(max_length=10000, null=True, blank=True)
    attachments = models.ForeignKey("files.FileCollection", on_delete=models.SET_NULL, null=True, blank=True)
    edited = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    score = models.DecimalField(default=0, max_digits=17, decimal_places=10)

    # Updates score based on Wilson score interval when creating/deleting comment votes
    @classmethod
    def comment_score_update(cls, instance, *args, **kwargs):
        comment = Comment.objects.filter(id=instance.comment.id
                                         ).annotate(upvotes=Count('commentvote',
                                                                  filter=Q(commentvote__vote=True)),
                                                    downvotes=Count('commentvote',
                                                                    filter=Q(commentvote__vote=False))
                                                    ).first()

        n = comment.upvotes + comment.downvotes

        if n == 0 or comment.upvotes - comment.downvotes == 0:
            return 0

        z = 1.281551565545
        p = float(comment.upvotes) / n

        left = p + 1 / (2 * n) * z * z
        right = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        under = 1 + 1 / n * z * z

        comment.score = (left - right) / under
        comment.save()

    class Meta:
        constraints = [models.CheckConstraint(check=Q(attachments__isnull=False) | Q(message__isnull=False),
                                              name='temp_comment_data_check')]


post_save.connect(Comment.comment_score_update, sender="comment.CommentVote")
post_delete.connect(Comment.comment_score_update, sender="comment.CommentVote")


class CommentVote(BaseModel):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    created_by = models.ForeignKey("user.User", on_delete=models.CASCADE)
    vote = models.BooleanField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['comment', 'created_by'], name='comment_vote_unique')]


def comment_section_create(*, active: bool = True) -> CommentSection:
    comments = CommentSection(active=active)
    comments.full_clean()
    comments.save()

    return comments


def comment_section_create_model_default() -> int:
    comment_section = CommentSection()
    comment_section.full_clean()
    comment_section.save()

    return comment_section.id


def comment_section_delete(*, comments_id: int):
    CommentSection.objects.get(comments_id=comments_id).delete()
