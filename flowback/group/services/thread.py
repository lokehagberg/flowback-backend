from rest_framework.exceptions import ValidationError

from flowback.comment.services import comment_create, comment_update, comment_delete, comment_vote
from flowback.common.services import get_object, model_update
from flowback.files.services import upload_collection
from flowback.group.models import GroupThread, GroupThreadVote
from flowback.group.notify import notify_group_thread
from flowback.group.selectors.permission import group_user_permissions
from flowback.notification.models import NotificationChannel


def group_thread_create(user_id: int,
                        group_id: int,
                        pinned: bool,
                        title: str,
                        description: str = None,
                        attachments: list = None,
                        work_group_id: int = None,
                        public: bool = True):
    group_user = group_user_permissions(user=user_id, group=group_id, work_group=work_group_id)

    if pinned:
        group_user_permissions(user=user_id, group=group_user.group, permissions=['admin'])

    if attachments:
        attachments = upload_collection(user_id=user_id,
                                        file=attachments,
                                        upload_to='group/thread')

    thread = GroupThread(created_by=group_user,
                         title=title,
                         description=description,
                         pinned=pinned,
                         attachments=attachments,
                         work_group_id=work_group_id,
                         public=public)

    thread.full_clean()
    thread.save()

    # Self-vote the thread
    group_thread_vote_update(user_id=user_id, thread_id=thread.id, vote=True)

    # Notify users when a thread is created
    notify_group_thread(message="A new thread has been posted",
                        action=NotificationChannel.Action.CREATED,
                        thread=thread)

    return thread


def group_thread_update(user_id: int, thread_id: int, data: dict):
    thread = get_object(GroupThread, id=thread_id)
    non_side_effect_fields = ['title', 'description', 'attachments', 'pinned']

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

    return comment


def group_thread_comment_update(fetched_by: int, thread_id: int, comment_id: int, data):
    thread = get_object(GroupThread, id=thread_id)
    group_user_permissions(user=fetched_by, group=thread.created_by.group)

    return comment_update(fetched_by=fetched_by,
                          comment_section_id=thread.comment_section_id,
                          comment_id=comment_id,
                          attachment_upload_to="group/thread/attachments",
                          data=data)


def group_thread_comment_delete(fetched_by: int, thread_id: int, comment_id: int):
    thread = get_object(GroupThread, id=thread_id)
    group_user = group_user_permissions(user=fetched_by, group=thread.created_by.group)

    return comment_delete(fetched_by=fetched_by,
                          comment_section_id=thread.comment_section_id,
                          comment_id=comment_id,
                          force=group_user.is_admin or group_user.user.is_superuser)


def group_thread_comment_vote(*, fetched_by: int, thread_id: int, comment_id: int, vote: bool = None):
    group_thread = GroupThread.objects.get(id=thread_id)
    group_user_permissions(user=fetched_by, group=group_thread.created_by.group)

    return comment_vote(fetched_by=fetched_by,
                        comment_section_id=group_thread.comment_section.id,
                        comment_id=comment_id,
                        vote=vote)


def group_thread_notification_subscribe(*, fetched_by: int, thread_id: int, **kwargs):
    group_thread = GroupThread.objects.get(id=thread_id)
    group_user = group_user_permissions(user=fetched_by, group=group_thread.created_by.group)

    group_thread.notification_channel.subscribe(user=group_user.user, **kwargs)
