from flowback.chat.models import DirectMessageUserData, GroupMessageUserData
from flowback.common.services import get_object
from flowback.group.selectors import group_user_permissions
from flowback.user.models import User


def direct_chat_timestamp(user_id: int, target: int, timestamp: int):
    user = get_object(User, id=user_id)
    target = get_object(User, id=target)
    DirectMessageUserData.objects.update_or_create(user=user, target=target, defaults=dict(timestamp=timestamp))
    return


def group_chat_timestamp(user_id: int, group_id: int, timestamp: int):
    group_user = group_user_permissions(group=group_id, user=user_id)
    GroupMessageUserData.objects.update_or_create(group_user=group_user, defaults=dict(timestamp=timestamp))
    return
