import django_filters
from django_filters import FilterSet

from flowback.user.models import User


class UserFilter(FilterSet):
    class Meta:
        model = User
        fields = {'id': [],
                  'username': ['icontains']
                  }


def get_user(user: int):
    return User.objects.get(user_id=user)


def user_list(*, filters=None):
    filters = filters or {}
    qs = User.objects.all()
    return UserFilter(filters, qs).qs
