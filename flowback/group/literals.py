from typing import Literal

# TODO make this automatic, preferrably each model should have a dedicated way to generate literals, returning
#  [str(LiteralName), [*fields]]
#  If possible, run it right after makemigrations method
GroupPermission = Literal[
    'allow_delegate',
    'allow_vote',
    'ban_members',
    'create_kanban_task',
    'create_poll',
    'create_proposal',
    'delete_kanban_task',
    'delete_proposal',
    'force_delete_comment',
    'force_delete_poll',
    'force_delete_proposal',
    'invite_user',
    'kick_members',
    'poll_fast_forward',
    'poll_quorum',
    'prediction_bet_create',
    'prediction_bet_delete',
    'prediction_bet_update',
    'prediction_statement_create',
    'prediction_statement_delete',
    'send_group_email',
    'update_kanban_task',
    'update_proposal'
]
