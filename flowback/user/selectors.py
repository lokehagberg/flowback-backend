import django_filters
from django_filters import FilterSet
from flowback.common.services import get_object
from flowback.user.models import User


class UserFilter(FilterSet):
    class Meta:
        model = User
        fields = {'id': ['exact'],
                  'username': ['exact', 'icontains']
                  }


def get_user(user: int):
    return get_object(User, id=user)


def user_list(*, filters=None):
    filters = filters or {}
    qs = User.objects.all()
    return UserFilter(filters, qs).qs
