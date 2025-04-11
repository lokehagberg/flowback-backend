from rest_framework.exceptions import ValidationError

from flowback.comment.models import Comment, CommentVote
from flowback.common.services import model_update, get_object
from flowback.files.services import upload_collection
from flowback.user.models import User


def comment_create(*,
                   author_id: int,
                   comment_section_id: int,
                   message: str = None,
                   parent_id: int,
                   attachments: list = None,
                   attachment_upload_to="",
                   attachment_upload_to_include_timestamp=True) -> Comment:

    if not (message or attachments):
        raise ValidationError("Comments can't be created without either a Message or Attachment(s)")

    if attachments:
        collection = upload_collection(user_id=author_id,
                                       file=attachments,
                                       upload_to=attachment_upload_to,
                                       upload_to_include_timestamp=attachment_upload_to_include_timestamp)

    else:
        collection = None

    comment = Comment(author_id=author_id, comment_section_id=comment_section_id,
                      message=message, parent_id=parent_id, attachments=collection)

    if parent_id:
        parent = get_object(Comment, id=parent_id)

        if not parent.active:
            raise ValidationError("Parent has already been removed")

    comment.full_clean()
    comment.save()

    return comment


def comment_update(*, fetched_by: int,
                   comment_section_id: int,
                   comment_id: int,
                   attachment_upload_to="",
                   attachment_upload_to_include_timestamp=True,
                   data) -> Comment:
    comment = get_object(Comment, comment_section_id=comment_section_id, id=comment_id)

    if 'attachments' in data.keys():
        collection = upload_collection(user_id=fetched_by,
                                       file=data['attachments'],
                                       upload_to=attachment_upload_to,
                                       upload_to_include_timestamp=attachment_upload_to_include_timestamp)

        data['attachments_id'] = collection.id

        if comment.attachments:
            comment.attachments.delete()

    else:
        collection = None

    if not comment.active:
        raise ValidationError("Parent has already been removed")

    if fetched_by != comment.author_id:
        raise ValidationError("Comment doesn't belong to User")

    data['edited'] = True
    non_side_effect_fields = ['message', 'edited', 'attachments_id']
    comment, has_updated = model_update(instance=comment,
                                        fields=non_side_effect_fields,
                                        data=data)

    return comment


def comment_delete(*, fetched_by: int, comment_section_id: int, comment_id: int, force: bool = False):
    comment = get_object(Comment, comment_section_id=comment_section_id, id=comment_id)
    if not (fetched_by == comment.author_id) and not force:
        raise ValidationError("Comment doesn't belong to User")

    if not comment.active:
        raise ValidationError("Comment has already been removed")

    if comment.attachments:
        comment.attachments.delete()

    comment.active = False
    comment.message = '[Deleted]'
    comment.save()


def comment_vote(*, fetched_by: int, comment_section_id: int, comment_id: int, vote: bool = None):
    comment = Comment.objects.get(comment_section_id=comment_section_id, id=comment_id)
    user = User.objects.get(id=fetched_by)

    if vote is None:
        try:
            return CommentVote.objects.get(created_by=user, comment=comment).delete()

        except CommentVote.DoesNotExist:
            raise ValidationError("User haven't voted on this comment")

    CommentVote.objects.update_or_create(defaults=dict(vote=vote), created_by=user, comment=comment)
