from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.group.serializers import GroupUserSerializer
from flowback.poll.selectors.area import poll_area_statement_list
from flowback.poll.services.area import poll_area_statement_create


@extend_schema(tags=['poll'])
class PollAreaStatementListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 25
        max_limit = 50

    class FilterSerializer(serializers.Serializer):
        order_by = serializers.ChoiceField(choices=['created_at', '-created_at', 'score', '-score'],
                                           required=False)
        vote = serializers.BooleanField(required=False, allow_null=True, default=None)
        tag = serializers.CharField(required=False)

    class OutputSerializer(serializers.Serializer):
        class SegmentSerializer(serializers.Serializer):
            tag_name = serializers.CharField(source='tag.name')

        created_by = GroupUserSerializer
        vote = serializers.BooleanField(allow_null=True)
        tags = SegmentSerializer(many=True, source='pollareastatementsegment_set')

    def get(self, request, poll_id: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        area_statements = poll_area_statement_list(user=request.user,
                                                   poll_id=poll_id,
                                                   filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=area_statements,
                                      request=request,
                                      view=self)