from rest_framework.exceptions import ValidationError

from flowback.common.services import get_object, model_update
from flowback.group.models import GroupTags
from flowback.group.selectors import group_user_permissions


def group_tag_create(*, user: int, group: int, name: str) -> GroupTags:
    group_user_permissions(user=user, group=group, permissions=['admin'])
    tag = GroupTags(name=name, group_id=group)
    tag.full_clean()
    tag.save()

    return tag


def group_tag_update(*, user: int, group: int, tag: int, data) -> GroupTags:
    group_user_permissions(user=user, group=group, permissions=['admin'])
    tag = get_object(GroupTags, group_id=group, id=tag)
    non_side_effect_fields = ['active']

    if (GroupTags.objects.filter(group_id=group, active=True).count() <= 1
            and tag.active
            and data.get('active')):
        raise ValidationError('Group must have at least one active tag available for users')

    group_tag, has_updated = model_update(instance=tag,
                                          fields=non_side_effect_fields,
                                          data=data)

    return group_tag


def group_tag_delete(*, user: int, group: int, tag: int) -> None:
    group_user_permissions(user=user, group=group, permissions=['admin'])
    tag = get_object(GroupTags, group_id=group, id=tag)

    if GroupTags.objects.filter(group_id=group, active=True).count() <= 1 and tag.active:
        raise ValidationError('Group must have at least one active tag available for users')

    tag.delete()
