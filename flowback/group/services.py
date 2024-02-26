from typing import Union

from django.core.mail import send_mass_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from backend.settings import env, DEFAULT_FROM_EMAIL
from rest_framework.exceptions import ValidationError

from flowback.comment.models import Comment
from flowback.comment.services import comment_create, comment_update, comment_delete
from flowback.kanban.models import KanbanEntry
from flowback.notification.services import NotificationManager
from flowback.schedule.models import ScheduleEvent
from flowback.schedule.services import ScheduleManager, subscribe_schedule
from flowback.kanban.services import KanbanManager
from flowback.user.services import user_schedule
from flowback.user.models import User
from flowback.group.models import Group, GroupUser, GroupUserInvite, GroupUserDelegator, GroupTags, GroupPermissions, \
    GroupUserDelegate, GroupUserDelegatePool, GroupThread
from flowback.group.selectors import group_user_permissions
from flowback.common.services import model_update, get_object

group_schedule = ScheduleManager(schedule_origin_name='group', possible_origins=['poll'])
group_kanban = KanbanManager(origin_type='group')
group_notification = NotificationManager(sender_type='group', possible_categories=['group', 'members', 'invite',
                                                                                   'delegate', 'poll', 'kanban',
                                                                                   'schedule'])


def group_notification_subscribe(*, user_id: int, group: int, categories: list[str]):
    user = group_user_permissions(user=user_id, group=group)

    if 'invite' in categories and (not user.is_admin or not user.permission.invite_user):
        raise ValidationError('Permission denied for invite notifications')

    group_notification.channel_subscribe(user_id=user_id, sender_id=group, category=categories)


def group_create(*, user: int, name: str, description: str, hide_poll_users: bool,
                 public: bool, direct_join: bool, image: str = None, cover_image: str = None) -> Group:
    user = get_object(User, id=user)

    if not (env('FLOWBACK_ALLOW_GROUP_CREATION') or (user.is_staff or user.is_superuser)):
        raise ValidationError('Permission denied')

    # Create Group
    group = Group(created_by=user, name=name, description=description, image=image,
                  cover_image=cover_image, hide_poll_users=hide_poll_users, public=public, direct_join=direct_join)
    # TODO Fullclean MUST work!
    # group.full_clean()
    group.save()

    # Generate GroupUser
    GroupUser.objects.create(user=user, group=group, is_admin=True)

    return group


def group_update(*, user: int, group: int, data) -> Group:
    group_user = group_user_permissions(group=group, user=user, permissions=['admin'])
    non_side_effect_fields = ['name', 'description', 'image', 'cover_image', 'hide_poll_users',
                              'public', 'direct_join', 'default_permission', 'default_quorum']

    # Check if group_permission exists to allow for a new default_permission
    if default_permission := data.get('default_permission'):
        data['default_permission'] = get_object(GroupPermissions, id=default_permission, author_id=group)

    group, has_updated = model_update(instance=group_user.group,
                                      fields=non_side_effect_fields,
                                      data=data)

    group_notification.create(sender_id=group.id, action=group_notification.Action.update, category='group',
                              message=f'{group_user.user.username} updated the group information in {group.name}')

    return group


def group_delete(*, user: int, group: int) -> None:
    group_user_permissions(group=group, user=user, permissions=['creator']).group.delete()


def group_permission_create(*,
                            user: int,
                            group: int,
                            role_name: str,
                            **permissions) -> GroupPermissions:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    group_permission = GroupPermissions(role_name=role_name, author_id=group, **permissions)
    group_permission.full_clean()
    group_permission.save()

    return group_permission


def group_permission_update(*, user: int, group: int, permission_id: int, data) -> GroupPermissions:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    non_side_effect_fields = ['role_name',
                              'invite_user',
                              'create_poll',
                              'poll_quorum'
                              'allow_vote',
                              'kick_members',
                              'ban_members',
                              'create_proposal',
                              'update_proposal',
                              'delete_proposal',
                              'force_delete_poll',
                              'force_delete_proposal',
                              'force_delete_comment']
    group_permission = get_object(GroupPermissions, id=permission_id, author_id=group)

    group_permission, has_updated = model_update(instance=group_permission,
                                                 fields=non_side_effect_fields,
                                                 data=data)

    return group_permission


def group_permission_delete(*, user: int, group: int, permission_id: int) -> None:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    get_object(GroupPermissions, id=permission_id).delete()


def group_mail(*, fetched_by: int, group: int, title: str, message: str) -> None:
    group_user = group_user_permissions(group=group, user=fetched_by, permissions=['admin'])

    subject = f'[{group_user.group.name}] - {title}'
    targets = GroupUser.objects.filter(group_id=group).values('user__email').all()

    send_mass_mail([subject, message, DEFAULT_FROM_EMAIL,
                    [target['user__email']]] for target in targets)


def group_join(*, user: int, group: int) -> Union[GroupUser, GroupUserInvite]:
    user = get_object(User, id=user)
    group = get_object(Group, id=group)

    if not group.public:
        raise ValidationError('Permission denied')

    get_object(GroupUser, 'User already joined', reverse=True, user=user, group=group)
    get_object(GroupUserInvite, 'User already requested invite', reverse=True, user=user, group=group)

    if not group.direct_join:
        user_status = GroupUserInvite(user=user, group=group, external=True)
        group_notification.create(sender_id=group.id, action=group_notification.Action.update,
                                  category='invite', message=f'User {user.username} requested to join {group.name}')

        user_status.full_clean()
        user_status.save()

    else:
        try:
            user_status = GroupUser.objects.get(user=user, group=group)
            user_status.active = True
            user_status.save()
        except GroupUser.DoesNotExist:
            user_status = GroupUser(user=user, group=group)
            user_status.full_clean()
            user_status.save()

    group_notification.create(sender_id=group.id, action=group_notification.Action.create,
                              category='members', message=f'User {user.username} joined the group {group.name}')

    return user_status


def group_user_update(*, user: int, group: int, fetched_by: int, data) -> GroupUser:
    user_to_update = group_user_permissions(group=group, user=fetched_by)
    non_side_effect_fields = []

    # If user updates someone else (requires Admin)
    if group_user_permissions(group=group, user=fetched_by, raise_exception=False, permissions=['admin']):
        user_to_update = group_user_permissions(group=group, user=user)
        non_side_effect_fields.extend(['permission_id', 'is_admin'])

    group_user, has_updated = model_update(instance=user_to_update,
                                           fields=non_side_effect_fields,
                                           data=data)

    return group_user


def group_leave(*, user: int, group: int) -> None:
    user = group_user_permissions(group=group, user=user)

    if user.user == user.group.created_by:
        raise ValidationError("Group owner isn't allowed to leave, deleting the group is an option")

    user.active = False
    user.save()

    group_notification.create(sender_id=group, action=group_notification.Action.create,
                              category='members', message=f'User {user.user.username} left the group {user.group.name}')


def group_invite(*, user: int, group: int, to: int) -> GroupUserInvite:
    group = group_user_permissions(group=group, user=user, permissions=['admin', 'invite_user']).group
    get_object(GroupUser, error_message='User is already in the group', reverse=True, group=group, user=to)
    invite = GroupUserInvite(user_id=to, group_id=group.id, external=False)

    invite.full_clean()
    invite.save()

    return invite


def group_invite_remove(*, user: int, group: int, to: int) -> None:
    group_user_permissions(group=group, user=user, permissions=['admin', 'invite_user'])
    invite = get_object(GroupUserInvite, 'User has not been invited', group_id=group, user_id=to)
    invite.delete()


def group_invite_accept(*, fetched_by: int, group: int, to: int = None) -> None:
    if to:
        group_user_permissions(group=group, user=fetched_by, permissions=['invite_user', 'admin'])
        get_object(GroupUser, 'User already joined', reverse=True, user_id=to, group=group)
        invite = get_object(GroupUserInvite, 'User has not requested invite', user_id=to, group_id=group, external=True)
        group_user = GroupUser(user_id=to, group_id=group)

    else:
        invite = get_object(GroupUserInvite, 'User has not been invited', user_id=fetched_by, group_id=group,
                            external=False)
        group_user = GroupUser(user_id=fetched_by, group_id=group)

    group_user.full_clean()
    group_user.save()
    invite.delete()


def group_invite_reject(*, fetched_by: id, group: int, to: int = None) -> None:
    if to:
        get_object(GroupUser, 'User already joined', reverse=True, user_id=to, group_id=group)
        group_user_permissions(group=group, user=fetched_by, permissions=['invite_user', 'admin'])
        invite = get_object(GroupUserInvite, 'User has not been invited', user_id=to, group_id=group)

    else:
        get_object(GroupUser, 'User already joined', reverse=True, user_id=fetched_by, group_id=group)
        invite = get_object(GroupUserInvite, 'User has not requested invite', user_id=fetched_by, group_id=group)

    invite.delete()


def group_tag_create(*, user: int, group: int, name: str) -> GroupTags:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    tag = GroupTags(name=name, group_id=group)
    tag.full_clean()
    tag.save()

    return tag


def group_tag_update(*, user: int, group: int, tag: int, data) -> GroupTags:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    tag = get_object(GroupTags, group_id=group, id=tag)
    non_side_effect_fields = ['active']

    group_tag, has_updated = model_update(instance=tag,
                                          fields=non_side_effect_fields,
                                          data=data)

    return group_tag


def group_tag_delete(*, user: int, group: int, tag: int) -> None:
    group_user_permissions(group=group, user=user, permissions=['admin'])
    tag = get_object(GroupTags, group_id=group, id=tag)
    tag.delete()


def group_user_delegate(*, user: int, group: int, delegate_pool_id: int, tags: list[int] = None) -> GroupUserDelegator:
    tags = tags or []
    delegator = group_user_permissions(group=group, user=user)
    delegate_pool = get_object(GroupUserDelegatePool, 'Delegate pool does not exist', id=delegate_pool_id, group=group)

    db_tags = GroupTags.objects.filter(id__in=tags, active=True).all()

    # Check if user_tags already exists
    user_tags = GroupTags.objects.filter(Q(groupuserdelegator__delegator=delegator,
                                           groupuserdelegator__group_id=group) &
                                         Q(id__in=tags))
    if user_tags.exists():
        raise ValidationError(f'User has already subscribed to '
                              f'{", ".join([x.name for x in user_tags.all()])}')

    # Check if tags exist in group
    if len(db_tags) < len(tags):
        raise ValidationError('Not all tags are available in the group')

    delegate_rel = GroupUserDelegator(group_id=group, delegator_id=delegator.id,
                                      delegate_pool_id=delegate_pool.id)
    delegate_rel.full_clean()
    delegate_rel.save()
    delegate_rel.tags.add(*db_tags)

    return delegate_rel


def group_user_delegate_update(*, user_id: int, group_id: int, data):
    group_user = group_user_permissions(user=user_id, group=group_id)

    tags = sum([x.get('tags', []) for x in data], [])
    tags_rel = {rel['delegate_pool_id']: rel['tags'] for rel in data}
    pools = [x.get('delegate_pool_id') for x in data]

    delegate_rel = GroupUserDelegator.objects.filter(delegator_id=group_user.id,
                                                     group_id=group_id,
                                                     delegate_pool__in=pools).all()

    if len(GroupTags.objects.filter(id__in=tags, active=True).all()) < len(tags):
        raise ValidationError('Not all tags are available in group')

    if len(delegate_rel) < len(pools):
        raise ValidationError('User is not delegator in all pools')

    TagsModel = GroupUserDelegator.tags.through
    TagsModel.objects.filter(groupuserdelegator__in=delegate_rel).delete()

    updated_tags = []
    for rel in delegate_rel:
        pk = rel.id
        for tag_pk in tags_rel[rel.delegate_pool.id]:
            updated_tags.append(TagsModel(groupuserdelegator_id=pk, grouptags_id=tag_pk))

    TagsModel.objects.bulk_create(updated_tags)


def group_user_delegate_remove(*, user_id: int, group_id: int, delegate_pool_id: int) -> None:
    delegator = group_user_permissions(group=group_id, user=user_id)
    delegate_pool = get_object(GroupUserDelegatePool, 'Delegate pool does not exist', id=delegate_pool_id)

    delegate_rel = get_object(GroupUserDelegator, 'User to delegate pool relation does not exist',
                              delegator=delegator, group_id=group_id, delegate_pool=delegate_pool)

    delegate_rel.delete()


def group_user_delegate_pool_create(*, user: int, group: int) -> GroupUserDelegatePool:
    group_user = group_user_permissions(user=user, group=group)

    # To avoid duplicates (for now)
    get_object(GroupUserDelegate, reverse=True, group=group, group_user=group_user)

    delegate_pool = GroupUserDelegatePool(group_id=group)
    delegate_pool.full_clean()
    delegate_pool.save()
    user_delegate = GroupUserDelegate(group_id=group, group_user=group_user, pool=delegate_pool)
    user_delegate.full_clean()
    user_delegate.save()

    group_notification.create(sender_id=group, action=group_notification.Action.update, category='delegate',
                              message=f'{group_user.user.username} is now a delegate in {group_user.group.name}')

    return delegate_pool


def group_user_delegate_pool_delete(*, user: int, group: int):
    group_user = group_user_permissions(user=user, group=group)

    delegate_user = get_object(GroupUserDelegate, group_user=group_user, group_id=group)
    delegate_pool = get_object(GroupUserDelegatePool, id=delegate_user.pool_id)

    group_notification.create(sender_id=group, action=group_notification.Action.update, category='delegate',
                              message=f'{group_user.user.username} has resigned from being a delegate in '
                                      f'{group_user.group.name}')

    delegate_pool.delete()


def group_schedule_event_create(*,
                                user_id: int,
                                group_id: int,
                                title: str,
                                start_date: timezone.datetime,
                                description: str = None,
                                end_date: timezone.datetime = None) -> ScheduleEvent:
    group_user = group_user_permissions(user=user_id, group=group_id)
    return group_schedule.create_event(schedule_id=group_user.group.schedule.id,
                                       title=title,
                                       start_date=start_date,
                                       end_date=end_date,
                                       origin_id=group_user.group.id,
                                       origin_name='group',
                                       description=description)


def group_schedule_event_update(*,
                                user_id: int,
                                group_id: int,
                                event_id: int,
                                **data):
    group_user = group_user_permissions(user=user_id, group=group_id)
    group_schedule.update_event(event_id=event_id, schedule_origin_id=group_user.group.id, data=data)


def group_schedule_event_delete(*,
                                user_id: int,
                                group_id: int,
                                event_id: int):
    group_user = group_user_permissions(user=user_id, group=group_id)
    group_schedule.delete_event(event_id=event_id, schedule_origin_id=group_user.group.id)


def group_schedule_subscribe(*,
                             user_id: int,
                             group_id: int):
    group_user = group_user_permissions(user=user_id, group=group_id)
    schedule = user_schedule.get_schedule(origin_id=user_id)
    target = group_user.group.schedule
    subscribe_schedule(schedule_id=schedule.id, target_id=target.id)


def group_kanban_entry_create(*,
                              group_id: int,
                              fetched_by_id: int,
                              assignee_id: int = None,
                              title: str,
                              description: str,
                              priority: int,
                              tag: int,
                              end_date: timezone.datetime = None
                              ) -> KanbanEntry:
    group_user_permissions(group=group_id, user=fetched_by_id, permissions=['admin', 'create_kanban_task'])
    return group_kanban.kanban_entry_create(origin_id=group_id,
                                            created_by_id=fetched_by_id,
                                            assignee_id=assignee_id,
                                            title=title,
                                            description=description,
                                            priority=priority,
                                            end_date=end_date,
                                            tag=tag)


def group_kanban_entry_update(*,
                              fetched_by_id: int,
                              group_id: int,
                              entry_id: int,
                              data) -> KanbanEntry:
    group_user_permissions(group=group_id, user=fetched_by_id, permissions=['admin', 'update_kanban_task'])
    return group_kanban.kanban_entry_update(origin_id=group_id,
                                            entry_id=entry_id,
                                            data=data)


def group_kanban_entry_delete(*,
                              fetched_by_id: int,
                              group_id: int,
                              entry_id: int):
    group_user_permissions(group=group_id, user=fetched_by_id, permissions=['admin', 'delete_kanban_task'])
    return group_kanban.kanban_entry_delete(origin_id=group_id, entry_id=entry_id)


def group_thread_create(user_id: int, group_id: int, pinned: bool, title: str):
    group_user = group_user_permissions(user=user_id, group=group_id)

    if pinned:
        group_user_permissions(user=user_id, group=group_user.group, permissions=['admin'])

    else:
        group_user_permissions(user=user_id, group=group_user.group)

    thread = GroupThread(created_by=group_user, title=title, pinned=pinned)
    thread.full_clean()
    thread.save()

    return thread


def group_thread_update(user_id: int, thread_id: int, data):
    thread = get_object(GroupThread, id=thread_id)
    non_side_effect_fields = ['title']

    if 'pinned' in data.keys():
        group_user_permissions(user=user_id, group=thread.created_by.group, permissions=['admin'])

    else:
        group_user_permissions(user=user_id, group=thread.created_by.group)

    thread, has_updated = model_update(instance=thread,
                                       fields=non_side_effect_fields,
                                       data=data)

    return thread


def group_thread_delete(user_id: int, thread_id: int):
    thread = get_object(GroupThread, id=thread_id)
    group_user_permissions(user=user_id, group=thread.created_by.group)

    thread.delete()


def group_thread_comment_create(user_id: int,
                                thread_id: int,
                                message: str,
                                attachments: list = None,
                                parent_id: int = None):
    thread = get_object(GroupThread, id=thread_id)
    group_user = group_user_permissions(user=user_id, group=thread.created_by.group)

    comment = comment_create(author_id=group_user.user.id,
                             comment_section_id=thread.comment_section.id,
                             message=message,
                             parent_id=parent_id,
                             attachments=attachments,
                             attachment_upload_to="group/thread/attachments")

    return comment


def group_thread_comment_update(user_id: int, thread_id: int, comment_id: int, data):
    thread = get_object(GroupThread, id=thread_id)
    comment = get_object(Comment, id=comment_id)

    group_user = group_user_permissions(user=user_id, group=thread.created_by.group)

    if comment.author != user_id and not group_user.is_admin:
        raise ValidationError('Comment is not owned by user.')

    return comment_update(fetched_by=user_id,
                          comment_section_id=thread.comment_section_id,
                          comment_id=comment_id,
                          data=data)


def group_thread_comment_delete(user_id: int, thread_id: int, comment_id: int):
    thread = get_object(GroupThread, id=thread_id)
    comment = get_object(Comment, id=comment_id)

    group_user = group_user_permissions(user=user_id, group=thread.created_by.group)

    if comment.author != user_id and not group_user.is_admin:
        raise ValidationError('Comment is not owned by user.')

    return comment_delete(fetched_by=user_id,
                          comment_section_id=thread.comment_section_id,
                          comment_id=comment_id)
