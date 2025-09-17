from rest_framework import serializers, status
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from rest_framework.response import Response
from rest_framework.views import APIView

# TODO Create, Update, Delete, Join, Leave, Delegate, Remove_Delegate