from rest_framework.exceptions import ValidationError

from flowback.comment.models import CommentSection, Comment
from flowback.common.services import model_update, get_object


def comment_section_create(*, active: bool = True) -> CommentSection:
    comments = CommentSection(active=active)
    comments.full_clean()
    comments.save()

    return comments


def comment_section_delete(*, comments_id: int):
    CommentSection.objects.get(comments_id=comments_id).delete()


def comment_create(*,
                   author_id: int,
                   comment_section_id: int,
                   message: str,
                   parent_id: int,
                   attachments: list) -> Comment:
    comment = Comment(author_id=author_id, comment_section_id=comment_section_id,
                      message=message, parent_id=parent_id, attachments=attachments)

    if parent_id:
        parent = get_object(Comment, id=parent_id)

        if not parent.active:
            raise ValidationError("Parent has already been removed")

    comment.full_clean()
    comment.save()

    return comment


def comment_update(*, fetched_by: int, comment_section_id: int,  comment_id: int, data) -> Comment:
    comment = get_object(Comment, comment_section_id=comment_section_id, id=comment_id)

    if not comment.active:
        raise ValidationError("Parent has already been removed")

    if fetched_by != comment.author_id:
        raise ValidationError("Comment doesn't belong to User")

    data['edited'] = True
    non_side_effect_fields = ['message', 'edited']
    comment, has_updated = model_update(instance=comment,
                                        fields=non_side_effect_fields,
                                        data=data)

    return comment


def comment_delete(*, fetched_by: int, comment_section_id: int, comment_id: int):
    comment = get_object(Comment, comment_section_id=comment_section_id, id=comment_id)
    if fetched_by != comment.author_id:
        raise ValidationError("Comment doesn't belong to User")

    if not comment.active:
        raise ValidationError("Comment has already been removed")

    comment.active = False
    comment.message = '[Deleted]'
    comment.save()
