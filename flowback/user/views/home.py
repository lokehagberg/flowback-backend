from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from flowback.common.pagination import get_paginated_response, LimitOffsetPagination
from flowback.group.serializers import GroupUserSerializer
from flowback.user.selectors import user_home_feed


@extend_schema(tags=['user'])
class UserHomeFeedAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 25
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        order_by = serializers.CharField(required=False)
        related_model = serializers.CharField(required=False)
        id = serializers.IntegerField(required=False)
        title__icontains = serializers.CharField(required=False)
        group_joined = serializers.BooleanField(required=False, allow_null=True, default=None)
        user_vote = serializers.BooleanField(required=False, allow_null=True, default=None)
        group_ids = serializers.CharField(required=False)


    class OutputSerializer(serializers.Serializer):
        created_by = GroupUserSerializer()
        created_at = serializers.DateTimeField()
        updated_at = serializers.DateTimeField()
        group_id = serializers.IntegerField()
        pinned = serializers.BooleanField()
        id = serializers.IntegerField()
        title = serializers.CharField()
        description = serializers.CharField(allow_null=True, default=None)
        related_model = serializers.CharField()
        group_joined = serializers.BooleanField()
        user_vote = serializers.BooleanField(allow_null=True, default=None)

    def get(self, request):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        home_feed = user_home_feed(fetched_by=request.user, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=home_feed,
                                      request=request,
                                      view=self)
