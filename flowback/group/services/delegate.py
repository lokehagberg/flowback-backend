from django.db.models import Q
from rest_framework.exceptions import ValidationError

from flowback.comment.models import Comment
from flowback.comment.services import comment_create, comment_update, comment_delete, comment_vote

from flowback.common.services import get_object
from flowback.group.models import GroupUserDelegator, GroupUserDelegatePool, GroupTags, GroupUserDelegate
from flowback.group.selectors import group_user_permissions
from flowback.group.services.group import group_notification


def group_user_delegate(*, user: int, group: int, delegate_pool_id: int, tags: list[int] = None) -> GroupUserDelegator:
    tags = tags or []
    delegator = group_user_permissions(user=user, group=group)
    delegate_pool = get_object(GroupUserDelegatePool, 'Delegate pool does not exist', id=delegate_pool_id, group=group)

    if GroupUserDelegate.objects.filter(group_user=delegator).exists():
        raise ValidationError('Delegator cannot be a delegate')

    db_tags = GroupTags.objects.filter(id__in=tags, active=True).all()

    # Check if user_tags already exists, user's can't have multiple delegators on a single tag
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


# TODO Likely needs an update
def group_user_delegate_update(*, user_id: int, group_id: int, data):
    group_user = group_user_permissions(user=user_id, group=group_id)

    tags = sum([x.get('tags', []) for x in data], [])
    tags_rel = {rel['delegate_pool_id']: rel['tags'] for rel in data}
    pools = [x.get('delegate_pool_id') for x in data]

    delegate_rel = GroupUserDelegator.objects.filter(delegator_id=group_user.id,
                                                     group_id=group_id,
                                                     delegate_pool__in=pools).all()


    if tags == 0:
        GroupUserDelegator.objects.filter(delegator=group_user, group_id=group_id, delegate_pool__in=pools).delete()
        return

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
    delegator = group_user_permissions(user=user_id, group=group_id)
    delegate_pool = get_object(GroupUserDelegatePool, 'Delegate pool does not exist', id=delegate_pool_id)

    delegate_rel = get_object(GroupUserDelegator, 'User to delegate pool relation does not exist',
                              delegator=delegator, group_id=group_id, delegate_pool=delegate_pool)

    delegate_rel.delete()


def group_user_delegate_pool_create(*, user: int, group: int, blockchain_id: int = None) -> GroupUserDelegatePool:
    group_user = group_user_permissions(user=user, group=group, permissions=['allow_delegate', 'admin'])

    if GroupUserDelegator.objects.filter(delegator=group_user).exists():
        GroupUserDelegator.objects.filter(delegator=group_user).delete()

    if GroupUserDelegate.objects.filter(group=group, group_user=group_user).exists():
        raise ValidationError('User is already a delegator')

    delegate_pool = GroupUserDelegatePool(group_id=group, blockchain_id=blockchain_id)
    delegate_pool.full_clean()
    delegate_pool.save()
    user_delegate = GroupUserDelegate(group_id=group,
                                      group_user=group_user,
                                      pool=delegate_pool)
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


def group_delegate_pool_comment_create(*,
                                       author_id: int,
                                       delegate_pool_id: int,
                                       message: str = None,
                                       attachments: list = None,
                                       parent_id: int = None) -> Comment:
    delegate_pool = get_object(GroupUserDelegatePool, id=delegate_pool_id)
    group_user_permissions(user=author_id, group=delegate_pool.group)

    comment = comment_create(author_id=author_id,
                             comment_section_id=delegate_pool.comment_section.id,
                             message=message,
                             parent_id=parent_id,
                             attachments=attachments,
                             attachment_upload_to="group/delegate_pool/comment/attachments")

    return comment


def group_delegate_pool_comment_update(*,
                                       fetched_by: int,
                                       delegate_pool_id: int,
                                       comment_id: int,
                                       data) -> Comment:
    delegate_pool = get_object(GroupUserDelegatePool, id=delegate_pool_id)
    group_user_permissions(user=fetched_by, group=delegate_pool.group)

    return comment_update(fetched_by=fetched_by,
                          comment_section_id=delegate_pool.comment_section.id,
                          comment_id=comment_id,
                          attachment_upload_to="group/delegate_pool/comment/attachments",
                          data=data)


def group_delegate_pool_comment_delete(*,
                                       fetched_by: int,
                                       delegate_pool_id: int,
                                       comment_id: int):
    delegate_pool = get_object(GroupUserDelegatePool, id=delegate_pool_id)
    group_user = group_user_permissions(user=fetched_by, group=delegate_pool.group)

    force = bool(group_user_permissions(group_user=group_user, permissions=['admin', 'force_delete_comment'],
                                        raise_exception=False))

    return comment_delete(fetched_by=fetched_by,
                          comment_section_id=delegate_pool.comment_section.id,
                          comment_id=comment_id,
                          force=force)


def group_delegate_pool_comment_vote(*, fetched_by: int, delegate_pool_id: int, comment_id: int, vote: bool):
    delegate_pool = GroupUserDelegatePool.objects.get(id=delegate_pool_id)
    group_user_permissions(user=fetched_by, group=delegate_pool.group)

    return comment_vote(fetched_by=fetched_by,
                        comment_section_id=delegate_pool.comment_section.id,
                        comment_id=comment_id,
                        vote=vote)
