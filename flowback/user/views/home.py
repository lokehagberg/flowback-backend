from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.views import APIView

from flowback.common.filters import NumberInFilter
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
        related_model = serializers.ChoiceField(required=False, choices=['poll', 'thread'])
        id = serializers.IntegerField(required=False)
        created_by_group_user_id = serializers.IntegerField(required=False, source='created_by_id')
        created_at__gt = serializers.DateTimeField(required=False)
        created_at__lt = serializers.DateTimeField(required=False)
        bookmarked = serializers.BooleanField(required=False, allow_null=True, default=None)

        work_group_ids = NumberInFilter(required=False)
        title__icontains = serializers.CharField(required=False)
        group_joined = serializers.BooleanField(required=False, allow_null=True, default=None)
        user_vote = serializers.BooleanField(required=False, allow_null=True, default=None)
        pinned = serializers.BooleanField(required=False, allow_null=True, default=None)
        group_ids = serializers.CharField(required=False)


    class OutputSerializer(serializers.Serializer):
        created_by = GroupUserSerializer(hide_relevant_users=True)
        created_at = serializers.DateTimeField()
        updated_at = serializers.DateTimeField()
        group_id = serializers.IntegerField()
        work_group_id = serializers.IntegerField(allow_null=True, default=None)
        pinned = serializers.BooleanField()
        id = serializers.IntegerField()
        title = serializers.CharField()
        description = serializers.CharField(allow_null=True, default=None)
        related_model = serializers.CharField()
        group_joined = serializers.BooleanField()
        user_vote = serializers.BooleanField(allow_null=True,
                                             default=None,
                                             help_text="Whether the user voted on a Poll, or in case of group threads, "
                                                       "the user's vote where None is not voted on.")

    def get(self, request):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        home_feed = user_home_feed(fetched_by=request.user, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=home_feed,
                                      request=request,
                                      view=self)
