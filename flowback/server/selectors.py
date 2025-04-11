from rest_framework.exceptions import PermissionDenied

from flowback.user.models import User, Report


def reports_list(fetched_by: User):
    if not fetched_by.is_staff or fetched_by.is_superuser:
        raise PermissionDenied('Only server staff members can view reports')

    return Report.objects.all().order_by('-created_at')