import django_filters
from django_filters import FilterSet
from rest_framework.exceptions import ValidationError

from flowback.common.services import get_object
from flowback.group.models import Group, GroupUser
from flowback.user.models import User
from backend.settings import env


class UserFilter(FilterSet):
    class Meta:
        model = User
        fields = {'id': ['exact'],
                  'username': ['exact', 'icontains']
                  }


def get_user(user: int):
    return get_object(User, id=user)


def user_list(*, fetched_by: User, filters=None):
    # Block access to this api for members, unless group admin or higher.
    if env('FLOWBACK_GROUP_ADMIN_USER_LIST_ACCESS_ONLY') \
            and not Group.objects.filter(created_by=fetched_by).exists() \
            and not GroupUser.objects.filter(user=fetched_by, is_admin=True) \
            and not (fetched_by.is_staff and fetched_by.is_superuser):
        raise ValidationError('User must be group admin or higher')

    filters = filters or {}
    qs = User.objects.all()
    return UserFilter(filters, qs).qs
