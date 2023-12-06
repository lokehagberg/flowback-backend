from django.shortcuts import render
from drf_spectacular.utils import extend_schema, OpenApiParameter

# Create your views here.
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView, Response

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.common.services import get_object
from flowback.group.serializers import GroupUserSerializer
from flowback.poll.models import Poll, PollProposal, PollVotingTypeRanking, PollVotingTypeForAgainst
from flowback.poll.selectors.poll import poll_list
from flowback.poll.selectors.prediction import poll_prediction_statement_list, poll_prediction_bet_list
from flowback.poll.selectors.proposal import poll_proposal_list, poll_user_schedule_list
from flowback.poll.selectors.vote import poll_vote_list, poll_delegates_list, delegate_poll_vote_list
from flowback.poll.selectors.comment import poll_comment_list

from flowback.poll.services.comment import poll_comment_create, poll_comment_update, poll_comment_delete
from flowback.poll.services.poll import poll_create, poll_update, poll_delete, poll_refresh_cheap, poll_notification, \
    poll_notification_subscribe
from flowback.poll.services.prediction import poll_prediction_statement_create, poll_prediction_statement_delete, \
    poll_prediction_bet_create, poll_prediction_bet_update, poll_prediction_bet_delete, poll_prediction_statement_vote_create, \
    poll_prediction_statement_vote_update, poll_prediction_statement_vote_delete
from flowback.poll.services.proposal import poll_proposal_create, poll_proposal_delete
from flowback.poll.services.vote import poll_proposal_vote_update, poll_proposal_delegate_vote_update

from flowback.comment.views import CommentListAPI, CommentCreateAPI, CommentUpdateAPI, CommentDeleteAPI


@extend_schema(tags=['home', 'poll'])
class PollListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        id_list = serializers.ListField(child=serializers.IntegerField(), required=False)
        order_by = serializers.CharField(default='created_at_desc')
        pinned = serializers.BooleanField(required=False, default=None, allow_null=True)

        title = serializers.CharField(required=False)
        title__icontains = serializers.CharField(required=False)
        poll_type = serializers.ChoiceField((0, 1, 2), required=False)
        tag = serializers.IntegerField(required=False)
        tag_name = serializers.CharField(required=False)
        tag_name__icontains = serializers.CharField(required=False)
        status = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class FileSerializer(serializers.Serializer):
            file = serializers.CharField()
            file_name = serializers.CharField()

        created_by = GroupUserSerializer()
        group_joined = serializers.BooleanField(required=False)
        group_id = serializers.IntegerField(source='created_by.group_id')
        group_name = serializers.CharField(source='created_by.group.name')
        group_image = serializers.ImageField(source='created_by.group.image')
        tag_name = serializers.CharField(source='tag.name', allow_null=True)
        attachments = FileSerializer(many=True, source='attachments.filesegment_set', allow_null=True)
        hide_poll_users = serializers.BooleanField(source='created_by.group.hide_poll_users')
        total_comments = serializers.IntegerField()

        proposal_end_date = serializers.DateTimeField(required=False)
        prediction_statement_end_date = serializers.DateTimeField(required=False)
        area_vote_end_date = serializers.DateTimeField(required=False)
        prediction_bet_end_date = serializers.DateTimeField(required=False)
        delegate_vote_end_date = serializers.DateTimeField(required=False)
        vote_end_date = serializers.DateTimeField(required=False)
        end_date = serializers.DateTimeField(required=False)

        class Meta:
            model = Poll
            fields = ('id',
                      'group_id',
                      'group_name',
                      'group_image',
                      'created_by',
                      'group_joined',
                      'hide_poll_users',
                      'title',
                      'description',
                      'poll_type',
                      'public',
                      'tag',
                      'tag_name',
                      'start_date',
                      'proposal_end_date',
                      'prediction_statement_end_date',
                      'area_vote_end_date',
                      'prediction_bet_end_date',
                      'delegate_vote_end_date',
                      'vote_end_date',
                      'end_date',
                      'result',
                      'participants',
                      'pinned',
                      'dynamic',
                      'total_comments',
                      'quorum',
                      'status',
                      'attachments')

    def get(self, request, group_id: int = None):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        polls = poll_list(fetched_by=request.user, group_id=group_id, filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=polls,
            request=request,
            view=self
        )


@extend_schema(tags=['poll'])
class PollNotificationSubscribeApi(APIView):
    class InputSerializer(serializers.Serializer):
        categories = serializers.MultipleChoiceField(choices=poll_notification.possible_categories)

    def post(self, request, poll: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_notification_subscribe(user_id=request.user.id, poll_id=poll, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll'])
class PollCreateAPI(APIView):
    class InputSerializer(serializers.ModelSerializer):
        tag = serializers.IntegerField()
        quorum = serializers.IntegerField(required=False)
        public = serializers.BooleanField(default=False)
        attachments = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)

        proposal_end_date = serializers.DateTimeField(required=False)
        prediction_statement_end_date = serializers.DateTimeField(required=False)
        area_vote_end_date = serializers.DateTimeField(required=False)
        prediction_bet_end_date = serializers.DateTimeField(required=False)
        delegate_vote_end_date = serializers.DateTimeField(required=False)
        vote_end_date = serializers.DateTimeField(required=False)
        end_date = serializers.DateTimeField(required=False)

        class Meta:
            model = Poll
            fields = ('title', 'description', 'start_date', 'proposal_end_date', 'prediction_statement_end_date',
                      'area_vote_end_date', 'prediction_bet_end_date', 'delegate_vote_end_date', 'vote_end_date',
                      'end_date', 'poll_type', 'public', 'tag', 'pinned', 'dynamic', 'quorum', 'attachments')

    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll = poll_create(user_id=request.user.id, group_id=group_id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=poll.id)


@extend_schema(tags=['poll'])
class PollUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        title = serializers.CharField(required=False)
        pinned = serializers.BooleanField(required=False)
        description = serializers.CharField(required=False)

    def post(self, request, poll: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll)  # TODO get celery
        poll_update(user_id=request.user.id, poll_id=poll, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll'])
class PollDeleteAPI(APIView):
    def post(self, request, poll: int):
        poll_refresh_cheap(poll_id=poll)  # TODO get celery
        poll_delete(user_id=request.user.id, poll_id=poll)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll'], deprecated=True)
class PollUserScheduleListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10
        max_limit = 500

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        order_by = serializers.CharField(required=False)
        poll_title = serializers.CharField(required=False)
        poll_title__icontains = serializers.CharField(required=False)
        start_date__lt = serializers.DateTimeField(required=False)
        start_date__gte = serializers.DateTimeField(required=False)
        end_date__lt = serializers.DateTimeField(required=False)
        end_date__gte = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        created_by = GroupUserSerializer()
        hide_poll_users = serializers.BooleanField(source='created_by.group.hide_poll_users')
        title = serializers.CharField(source='poll.title')
        description = serializers.CharField(source='poll.description')
        start_date = serializers.DateTimeField(source='pollproposaltypeschedule.event.start_date')
        end_date = serializers.DateTimeField(source='pollproposaltypeschedule.event.end_date')

        class Meta:
            model = PollProposal
            fields = ('id',
                      'created_by',
                      'hide_poll_users',
                      'title',
                      'description',
                      'poll',
                      'score',
                      'start_date',
                      'end_date')

    def get(self, request):
        filter_serializer = self.FilterSerializer(data=request.query_params)

        filter_serializer.is_valid(raise_exception=True)
        proposals = poll_user_schedule_list(fetched_by=request.user, filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=proposals,
            request=request,
            view=self
        )


@extend_schema(tags=['poll'])
class PollDelegatesListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        created_by = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = PollProposal
            fields = ('created_by',)

    def get(self, request, poll: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll)  # TODO get celery

        delegates = poll_delegates_list(fetched_by=request.user, poll_id=poll,
                                        filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=delegates,
            request=request,
            view=self
        )

