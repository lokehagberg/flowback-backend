from rest_framework.exceptions import ValidationError, PermissionDenied

from flowback.common.services import model_update
from flowback.group.models import WorkGroup, WorkGroupUser, WorkGroupUserJoinRequest
from flowback.group.selectors import group_user_permissions


def work_group_create(*, user_id: int, group_id: int, name: str, direct_join: bool) -> WorkGroup:
    group_user = group_user_permissions(user=user_id, group=group_id, permissions=['admin'])

    work_group = WorkGroup(name=name, direct_join=direct_join, group=group_user.group)
    work_group.full_clean()
    work_group.save()

    return work_group


def work_group_update(*, user_id: int, work_group_id: int, data) -> WorkGroup:
    work_group = WorkGroup.objects.get(id=work_group_id)
    group_user_permissions(user=user_id, group=work_group.group, permissions=['admin'])

    available_fields = ['name', 'direct_join']

    instance, has_updated = model_update(instance=work_group,
                                         fields=available_fields,
                                         data=data)

    return instance


def work_group_delete(*, user_id: int, work_group_id: int) -> None:
    work_group = WorkGroup.objects.get(id=work_group_id)
    group_user_permissions(user=user_id, group=work_group.group, permissions=['admin'])

    work_group.delete()


def work_group_user_join(*, user_id: int, work_group_id: int) -> int | None:
    work_group = WorkGroup.objects.get(id=work_group_id)
    group_user = group_user_permissions(user=user_id, group=work_group.group)

    if work_group.direct_join:
        work_group_user = WorkGroupUser(group_user=group_user, work_group=work_group)
        work_group_user.full_clean()
        work_group_user.save()
        return work_group_user.id

    else:
        work_group_user_join_request = WorkGroupUserJoinRequest(group_user=group_user, work_group=work_group)
        work_group_user_join_request.full_clean()
        work_group_user_join_request.save()


def work_group_user_leave(*, user_id: int, work_group_id: int) -> None:
    work_group = WorkGroup.objects.get(id=work_group_id)
    group_user = group_user_permissions(user=user_id, group=work_group.group)

    WorkGroupUser.objects.get(group_user=group_user, work_group=work_group).delete()


def work_group_user_add(*, user_id: int,
                        work_group_id: int,
                        target_group_user_id: int,
                        is_moderator: bool) -> WorkGroupUser:
    work_group = WorkGroup.objects.get(id=work_group_id)
    group_user = group_user_permissions(user=user_id, group=work_group.group)

    try:
        work_group_user = WorkGroupUser.objects.get(group_user=group_user, work_group=work_group)
        work_group_user_is_moderator = work_group_user.is_moderator

    except WorkGroupUser.DoesNotExist:
        work_group_user_is_moderator = False

    if group_user.is_admin or work_group_user_is_moderator:
        target_group_user = group_user_permissions(group_user=target_group_user_id)

        if WorkGroupUser.objects.filter(group_user=target_group_user, work_group=work_group).exists():
            raise ValidationError("User is already in the working group.")

        work_group_user_join_request = WorkGroupUserJoinRequest.objects.filter(group_user_id=target_group_user_id,
                                                                               work_group=work_group)

        if work_group_user_join_request.exists():
            work_group_user = WorkGroupUser(group_user=target_group_user,
                                            work_group=work_group,
                                            is_moderator=is_moderator
                                            if work_group_user_is_moderator or group_user.is_admin
                                            else False)
            work_group_user.full_clean()
            work_group_user.save()

            return work_group_user

    raise PermissionDenied()


def work_group_user_remove(*, user_id: int, work_group_id: int, target_group_user_id: int) -> None:
    work_group = WorkGroup.objects.get(id=work_group_id)
    group_user = group_user_permissions(user=user_id, group=work_group.group)

    try:
        work_group_user = WorkGroupUser.objects.get(group_user=group_user, work_group=work_group)
        work_group_user_is_moderator = work_group_user.is_moderator

    except WorkGroupUser.DoesNotExist:
        work_group_user_is_moderator = False

    if group_user.is_admin or work_group_user_is_moderator:
        target_group_user = group_user_permissions(user=target_group_user_id, group=work_group.group)

        WorkGroupUser.objects.get(group_user=target_group_user, work_group=work_group).delete()

    raise PermissionDenied()


def work_group_user_update(*, user_id: int, work_group_id: int, target_group_user_id: int, data) -> WorkGroupUser:
    work_group = WorkGroup.objects.get(id=work_group_id)
    group_user = group_user_permissions(user=user_id, group=work_group.group)
    work_group_user = WorkGroupUser.objects.get(group_user=group_user, work_group=work_group)

    if not work_group_user.is_moderator or group_user.is_admin:
        raise PermissionDenied("Requires work group moderator permission or admin.")

    available_fields = ['is_moderator']

    target_work_group_user = WorkGroupUser.objects.get(group_user=target_group_user_id, work_group=work_group)
    instance, has_updated = model_update(instance=target_work_group_user,
                                         fields=available_fields,
                                         data=data)

    return instance
