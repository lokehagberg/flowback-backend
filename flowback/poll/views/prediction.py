from drf_spectacular.utils import extend_schema

from rest_framework import serializers, status
from rest_framework.views import APIView, Response

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.group.serializers import GroupUserSerializer

from ..selectors.prediction import poll_prediction_statement_list, poll_prediction_bet_list
from ..services.prediction import (poll_prediction_statement_create,
                                   poll_prediction_statement_delete,
                                   poll_prediction_bet_create,
                                   poll_prediction_bet_update,
                                   poll_prediction_bet_delete,
                                   poll_prediction_statement_vote_create,
                                   poll_prediction_statement_vote_update,
                                   poll_prediction_statement_vote_delete)


@extend_schema(tags=['poll/prediction'])
class PollPredictionStatementListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 100
        default_limit = 25

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        poll_id = serializers.IntegerField(required=False)
        proposals = serializers.CharField(required=False)
        title = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        created_by_id = serializers.IntegerField(required=False)
        user_prediction_bet_exists = serializers.BooleanField(required=False)
        user_vote_exists = serializers.BooleanField(required=False)

    class OutputSerializer(serializers.Serializer):
        class StatementSegment(serializers.Serializer):
            proposal_id = serializers.IntegerField(source='proposal.id')
            proposal_title = serializers.CharField(source='proposal.title', required=False)
            proposal_description = serializers.CharField(source='proposal.description', required=False)
            is_true = serializers.BooleanField()

        id = serializers.IntegerField()
        poll_id = serializers.IntegerField()
        title = serializers.CharField()
        description = serializers.CharField(allow_null=True)
        attachments = serializers.ListField(child=serializers.FileField(), allow_null=True)
        created_by = GroupUserSerializer()
        end_date = serializers.DateTimeField()
        user_prediction_bet = serializers.IntegerField(required=False)
        user_prediction_statement_vote = serializers.BooleanField(required=False)
        combined_bet = serializers.FloatField()
        blockchain_id = serializers.IntegerField(allow_null=True)

        segments = StatementSegment(source='pollpredictionstatementsegment_set', many=True)

    def get(self, request, group_id: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        prediction_statement = poll_prediction_statement_list(fetched_by=request.user,
                                                              group_id=group_id,
                                                              filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=prediction_statement,
            request=request,
            view=self
        )


@extend_schema(tags=['poll/prediction'])
class PollPredictionBetListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 100
        default_limit = 25

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        created_by_id = serializers.IntegerField(required=False)
        prediction_statement_id = serializers.IntegerField(required=False)
        score = serializers.IntegerField(required=False)
        score__lt = serializers.IntegerField(required=False)
        score__gt = serializers.IntegerField(required=False)
        created_at__lt = serializers.DateTimeField(required=False)
        created_at__gt = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        prediction_statement_id = serializers.IntegerField()
        created_by = GroupUserSerializer()
        blockchain_id = serializers.IntegerField(allow_null=True)
        score = serializers.IntegerField()

    def get(self, request, group_id: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        predictions = poll_prediction_bet_list(fetched_by=request.user, group_id=group_id,
                                               filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=predictions,
            request=request,
            view=self
        )


@extend_schema(tags=['poll/prediction'])
class PollPredictionStatementCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        class SegmentSerializer(serializers.Serializer):
            proposal_id = serializers.IntegerField()
            is_true = serializers.BooleanField()

        title = serializers.CharField()
        description = serializers.CharField(required=False)
        end_date = serializers.DateTimeField()
        segments = SegmentSerializer(many=True)
        blockchain_id = serializers.IntegerField(required=False, allow_null=True)
        attachments = serializers.ListField(child=serializers.FileField(), required=False)

    def post(self, request, poll_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created_id = poll_prediction_statement_create(poll=poll_id,
                                                      user=request.user,
                                                      **serializer.validated_data)

        return Response(created_id, status=status.HTTP_201_CREATED)


@extend_schema(tags=['poll/prediction'])
class PollPredictionStatementDeleteAPI(APIView):
    def post(self, request, prediction_statement_id: int):
        poll_prediction_statement_delete(user=request.user,
                                         prediction_statement_id=prediction_statement_id)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll/prediction'])
class PollPredictionBetUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        score = serializers.IntegerField()
        blockchain_id = serializers.IntegerField(min_value=1, required=False)

    def post(self, request, prediction_statement_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        poll_prediction_bet_update(user=request.user, prediction_statement_id=prediction_statement_id,
                                   data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll/prediction'])
class PollPredictionBetDeleteAPI(APIView):
    def post(self, request, prediction_statement_id: int):
        poll_prediction_bet_delete(user=request.user, prediction_statement_id=prediction_statement_id)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll/prediction'])
class PollPredictionStatementVoteCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        vote = serializers.BooleanField()

    def post(self, request, prediction_statement_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_prediction_statement_vote_create(user=request.user,
                                              prediction_statement_id=prediction_statement_id,
                                              **serializer.validated_data)

        return Response(status=status.HTTP_201_CREATED)


@extend_schema(tags=['poll/prediction'])
class PollPredictionStatementVoteUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        vote = serializers.BooleanField()

    def post(self, request, prediction_statement_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_prediction_statement_vote_update(user=request.user,
                                              prediction_statement_id=prediction_statement_id,
                                              data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll/prediction'])
class PollPredictionStatementVoteDeleteAPI(APIView):
    def post(self, request, prediction_statement_id: int):
        poll_prediction_statement_vote_delete(user=request.user,
                                              prediction_statement_id=prediction_statement_id)

        return Response(status=status.HTTP_200_OK)
