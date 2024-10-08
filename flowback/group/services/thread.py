from rest_framework.exceptions import ValidationError

from flowback.comment.models import Comment
from flowback.comment.services import comment_create, comment_update, comment_delete, comment_vote
from flowback.common.services import get_object, model_update
from flowback.files.services import upload_collection
from flowback.group.models import GroupThread, GroupThreadVote
from flowback.group.selectors import group_user_permissions
from flowback.notification.services import NotificationManager

group_thread_notification = NotificationManager(sender_type='group_thread', possible_categories=['comment'])


def group_thread_create(user_id: int,
                        group_id: int,
                        pinned: bool,
                        title: str,
                        description: str = None,
                        attachments: list = None):
    group_user = group_user_permissions(user=user_id, group=group_id)

    if pinned:
        group_user_permissions(user=user_id, group=group_user.group, permissions=['admin'])

    else:
        group_user_permissions(user=user_id, group=group_user.group)

    if attachments:
        attachments = upload_collection(user_id=user_id,
                                        file=attachments,
                                        upload_to='group/thread')

    thread = GroupThread(created_by=group_user,
                         title=title,
                         description=description,
                         pinned=pinned,
                         attachments=attachments)

    thread.full_clean()
    thread.save()

    return thread


def group_thread_update(user_id: int, thread_id: int, data: dict):
    thread = get_object(GroupThread, id=thread_id)
    non_side_effect_fields = ['title', 'description', 'attachments']

    if 'pinned' in data.keys():
        group_user_permissions(user=user_id, group=thread.created_by.group, permissions=['admin'])

    else:
        group_user_permissions(user=user_id, group=thread.created_by.group)

    if 'attachments' in data.keys():
        data['attachments'] = upload_collection(user_id=user_id,
                                                file=data.pop('attachments'),
                                                upload_to='group/thread')

    thread, has_updated = model_update(instance=thread,
                                       fields=non_side_effect_fields,
                                       data=data)

    return thread


def group_thread_delete(user_id: int, thread_id: int):
    thread = get_object(GroupThread, id=thread_id)
    group_user_permissions(user=user_id, group=thread.created_by.group)

    thread.delete()


def group_thread_vote_update(user_id: int, thread_id: int, vote: bool = None):
    try:
        thread = GroupThread.objects.get(id=thread_id)

    except GroupThread.DoesNotExist:
        raise ValidationError('Thread does not exist')

    group_user = group_user_permissions(user=user_id, group=thread.created_by.group)

    if vote is None:
        try:
            GroupThreadVote.objects.get(created_by=group_user, thread=thread).delete()
            return
        except GroupThreadVote.DoesNotExist:
            raise ValidationError('Vote does not exist')

    GroupThreadVote.objects.update_or_create(defaults=dict(vote=vote), thread=thread, created_by=group_user)


def group_thread_comment_create(author_id: int,
                                thread_id: int,
                                message: str = None,
                                attachments: list = None,
                                parent_id: int = None):
    thread = get_object(GroupThread, id=thread_id)
    group_user = group_user_permissions(user=author_id, group=thread.created_by.group)

    comment = comment_create(author_id=group_user.user.id,
                             comment_section_id=thread.comment_section.id,
                             message=message,
                             parent_id=parent_id,
                             attachments=attachments,
                             attachment_upload_to="group/thread/attachments")

    group_thread_notification.create(sender_id=thread.id,
                                     related_id=comment.id,
                                     action=group_thread_notification.Action.create,
                                     category='comment',
                                     message=f'User "{group_user.user.username}" commented on thread "{thread.title}"')

    return comment


def group_thread_notification_subscribe(user_id: int, thread_id: int, categories: list[str]):
    thread = get_object(GroupThread, id=thread_id)
    group_user_permissions(user=user_id, group=thread.created_by.group)

    group_thread_notification.channel_subscribe(user_id=user_id,
                                         sender_id=thread.id,
                                         category=categories)

    return True


def group_thread_comment_update(author_id: int, thread_id: int, comment_id: int, data):
    thread = get_object(GroupThread, id=thread_id)
    comment = get_object(Comment, id=comment_id)

    group_user = group_user_permissions(user=author_id, group=thread.created_by.group)

    if comment.author.id != author_id and not group_user.is_admin:
        raise ValidationError('Comment is not owned by user.')

    return comment_update(fetched_by=author_id,
                          comment_section_id=thread.comment_section_id,
                          comment_id=comment_id,
                          data=data)


def group_thread_comment_delete(author_id: int, thread_id: int, comment_id: int):
    thread = get_object(GroupThread, id=thread_id)
    comment = get_object(Comment, id=comment_id)

    group_user = group_user_permissions(user=author_id, group=thread.created_by.group)

    if comment.author.id != author_id and not group_user.is_admin:
        raise ValidationError('Comment is not owned by user.')

    return comment_delete(fetched_by=author_id,
                          comment_section_id=thread.comment_section_id,
                          comment_id=comment_id)


def group_thread_comment_vote(*, user: int, thread_id: int, comment_id: int, vote: bool = None):
    group_thread = GroupThread.objects.get(id=thread_id)
    group_user_permissions(user=user, group=group_thread.created_by.group)

    return comment_vote(fetched_by=user,
                        comment_section_id=group_thread.comment_section.id,
                        comment_id=comment_id,
                        vote=vote)
