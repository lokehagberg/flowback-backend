from flowback.chat.models import DirectMessageUserData, GroupMessageUserData
from flowback.common.services import get_object
from flowback.group.selectors import group_user_permissions
from flowback.user.models import User


def direct_chat_timestamp(user_id: int, target: int, **data):
    user = get_object(User, id=user_id)
    target = get_object(User, id=target)
    DirectMessageUserData.objects.update_or_create(user_id=user, target_id=target, **data)
    return


def group_chat_timestamp(user_id: int, group_id: int, **data):
    group_user = group_user_permissions(group=group_id, user=user_id)
    GroupMessageUserData.objects.update_or_create(group_user=group_user, **data)
    return
