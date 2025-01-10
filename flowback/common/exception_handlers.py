import traceback
from pprint import pprint

from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied
from django.http import Http404

from rest_framework.views import exception_handler
from rest_framework import exceptions
from rest_framework.serializers import as_serializer_error
from django.core.exceptions import ObjectDoesNotExist
from backend.settings import DEBUG


# The default exception handler
def drf_default_with_modifications_exception_handler(exc, ctx):

    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()

    if isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, ObjectDoesNotExist):
        if DEBUG:
            tb = ''.join(traceback.TracebackException.from_exception(exc).format())
            print(tb)  # Print exception for reference

        exc = exceptions.NotFound(detail=str(exc))

    response = exception_handler(exc, ctx)

    # If unexpected error occurs (server error, etc.)
    if response is None:
        return response

    if isinstance(exc.detail, (list, dict)):
        response.data = {
            "detail": response.data
        }

    return response
