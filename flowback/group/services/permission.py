from flowback.common.services import get_object, model_update
from flowback.group.models import GroupPermissions
from flowback.group.selectors import group_user_permissions


def group_permission_create(*,
                            user: int,
                            group: int,
                            role_name: str,
                            **permissions) -> GroupPermissions:
    group_user_permissions(user=user, group=group, permissions=['admin'])
    group_permission = GroupPermissions(role_name=role_name, author_id=group, **permissions)
    group_permission.full_clean()
    group_permission.save()

    return group_permission


def group_permission_update(*, user: int, group: int, permission_id: int, data) -> GroupPermissions:
    group_user_permissions(user=user, group=group, permissions=['admin'])
    non_side_effect_fields = ['role_name',
                              'invite_user',
                              'create_poll',
                              'poll_fast_forward',
                              'poll_quorum',
                              'allow_vote',
                              'allow_delegate',
                              'kick_members',
                              'ban_members',
                              'send_group_email',

                              'create_proposal',
                              'update_proposal',
                              'delete_proposal',

                              'prediction_statement_create',
                              'prediction_statement_delete',

                              'prediction_bet_create',
                              'prediction_bet_update',
                              'prediction_bet_delete',

                              'create_kanban_task',
                              'update_kanban_task',
                              'delete_kanban_task',

                              'force_delete_poll',
                              'force_delete_proposal',
                              'force_delete_comment']
    group_permission = get_object(GroupPermissions, id=permission_id, author_id=group)

    group_permission, has_updated = model_update(instance=group_permission,
                                                 fields=non_side_effect_fields,
                                                 data=data)

    return group_permission


def group_permission_delete(*, user: int, group: int, permission_id: int) -> None:
    group_user_permissions(user=user, group=group, permissions=['admin'])
    get_object(GroupPermissions, id=permission_id).delete()
