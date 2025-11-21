from django.shortcuts import render
from drf_spectacular.utils import extend_schema

# Create your views here.
from rest_framework import serializers, status
from rest_framework.views import APIView, Response

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response

from flowback.group.serializers import GroupUserSerializer
from flowback.notification.views import NotificationSubscribeTemplateAPI
from flowback.poll.models import Poll, PollProposal
from flowback.poll.selectors.poll import poll_list, poll_phase_template_list
from flowback.poll.selectors.proposal import poll_user_schedule_list
from flowback.poll.selectors.vote import poll_delegates_list

from flowback.poll.services.poll import (poll_create, poll_update, poll_delete, poll_fast_forward,
                                         poll_phase_template_create, poll_phase_template_update,
                                         poll_phase_template_delete, poll_notification_subscribe)


@extend_schema(tags=['home', 'poll'])
class PollListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        id_list = serializers.CharField(required=False)
        order_by = serializers.CharField(default='start_date_desc',
                                         required=False)  # TODO add desc, add a way to limit order_by fields to two.
        pinned = serializers.BooleanField(required=False, default=None, allow_null=True)

        title = serializers.CharField(required=False)
        title__icontains = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        description__icontains = serializers.ListField(child=serializers.CharField(), required=False)
        poll_type = serializers.ChoiceField((0, 1, 2), required=False)
        tag_id = serializers.IntegerField(required=False)
        tag_name = serializers.CharField(required=False)
        tag_name__icontains = serializers.ListField(child=serializers.CharField(), required=False)
        has_attachments = serializers.BooleanField(required=False, allow_null=True, default=None)
        status = serializers.IntegerField(required=False)
        phase = serializers.CharField(required=False)
        work_group_ids = serializers.CharField(required=False)

        # Blob of gt and lt filter fields
        start_date__gt = serializers.DateTimeField(required=False)
        start_date__lt = serializers.DateTimeField(required=False)
        area_vote_end_date__gt = serializers.DateTimeField(required=False)
        area_vote_end_date__lt = serializers.DateTimeField(required=False)
        proposal_end_date__gt = serializers.DateTimeField(required=False)
        proposal_end_date__lt = serializers.DateTimeField(required=False)
        prediction_statement_end_date__gt = serializers.DateTimeField(required=False)
        prediction_statement_end_date__lt = serializers.DateTimeField(required=False)
        prediction_bet_end_date__gt = serializers.DateTimeField(required=False)
        prediction_bet_end_date__lt = serializers.DateTimeField(required=False)
        delegate_vote_end_date__gt = serializers.DateTimeField(required=False)
        delegate_vote_end_date__lt = serializers.DateTimeField(required=False)
        vote_end_date__gt = serializers.DateTimeField(required=False)
        vote_end_date__lt = serializers.DateTimeField(required=False)
        end_date__gt = serializers.DateTimeField(required=False)
        end_date__lt = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class FileSerializer(serializers.Serializer):
            file = serializers.CharField()
            file_name = serializers.CharField()

        created_by = GroupUserSerializer(allow_null=True, hide_relevant_users=True)
        group_joined = serializers.BooleanField(required=False)
        group_id = serializers.IntegerField(source='created_by.group_id')
        group_name = serializers.CharField(source='created_by.group.name')
        group_image = serializers.ImageField(source='created_by.group.image')
        tag_id = serializers.IntegerField(allow_null=True)
        tag_name = serializers.CharField(source='tag.name', allow_null=True)
        attachments = FileSerializer(many=True, source="attachments.filesegment_set", allow_null=True)
        hide_poll_users = serializers.BooleanField(source='created_by.group.hide_poll_users')
        total_comments = serializers.IntegerField()
        total_proposals = serializers.IntegerField()
        total_predictions = serializers.IntegerField()
        work_group_id = serializers.IntegerField(allow_null=True)
        work_group_name = serializers.CharField(source='work_group.name', allow_null=True)

        proposal_end_date = serializers.DateTimeField(required=False)
        prediction_statement_end_date = serializers.DateTimeField(required=False)
        area_vote_end_date = serializers.DateTimeField(required=False)
        prediction_bet_end_date = serializers.DateTimeField(required=False)
        delegate_vote_end_date = serializers.DateTimeField(required=False)
        vote_end_date = serializers.DateTimeField(required=False)
        end_date = serializers.DateTimeField(required=False)
        phase = serializers.CharField()

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
                      'allow_fast_forward',
                      'public',
                      'blockchain_id',
                      'tag_id',
                      'tag_name',
                      'start_date',
                      'proposal_end_date',
                      'prediction_statement_end_date',
                      'schedule_poll_meeting_link',
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
                      'total_proposals',
                      'total_predictions',
                      'quorum',
                      'status',
                      'status_prediction',
                      'interval_mean_absolute_correctness',
                      'attachments',
                      'work_group_id',
                      'work_group_name',
                      'phase')

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
class PollCreateAPI(APIView):
    class InputSerializer(serializers.ModelSerializer):
        tag = serializers.IntegerField(required=False)
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
        work_group_id = serializers.IntegerField(required=False)

        class Meta:
            model = Poll
            fields = ('title',
                      'description',
                      'start_date',
                      'proposal_end_date',
                      'prediction_statement_end_date',
                      'area_vote_end_date',
                      'prediction_bet_end_date',
                      'delegate_vote_end_date',
                      'schedule_poll_meeting_link',
                      'end_date',
                      'poll_type',
                      'blockchain_id',
                      'public',
                      'allow_fast_forward',
                      'tag',
                      'pinned',
                      'dynamic',
                      'quorum',
                      'work_group_id',
                      'attachments')

    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll = poll_create(user_id=request.user.id, group_id=group_id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=poll.id)


@extend_schema(tags=['poll'])
class PollUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        title = serializers.CharField(required=False)
        pinned = serializers.BooleanField(required=False, allow_null=True, default=None)
        schedule_poll_meeting_link = serializers.CharField(required=False, allow_null=True)
        description = serializers.CharField(required=False)

    def post(self, request, poll: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_update(user_id=request.user.id, poll_id=poll, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll'],
               description="Forwards the poll into the next phase. For example: if the poll is in area vote, it will go to proposal creation")
class PollFastForwardAPI(APIView):
    class InputSerializer(serializers.Serializer):
        phase = serializers.CharField()

    def post(self, request, poll_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_fast_forward(user_id=request.user.id, poll_id=poll_id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll'])
class PollDeleteAPI(APIView):
    def post(self, request, poll: int):
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
        start_date = serializers.DateTimeField(source='pollproposaltypeschedule.event_start_date')
        end_date = serializers.DateTimeField(source='pollproposaltypeschedule.event_end_date')

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
            view=self)


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

        delegates = poll_delegates_list(fetched_by=request.user, poll_id=poll,
                                        filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=delegates,
            request=request,
            view=self
        )


@extend_schema(tags=['poll'])
class PollPhaseTemplateListAPI(APIView):
    class FilterSerializer(serializers.Serializer):
        order_by = serializers.ChoiceField(choices=['created_at_asc', 'created_at_desc'], required=False)
        created_by_group_user_id = serializers.IntegerField(required=False)
        name = serializers.CharField(required=False)
        name__icontains = serializers.CharField(required=False)
        poll_type = serializers.IntegerField(required=False, min_value=1, max_value=4)
        poll_is_dynamic = serializers.BooleanField(required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        created_by_group_user = GroupUserSerializer()
        name = serializers.CharField(max_length=255)
        poll_type = serializers.IntegerField(max_value=4, min_value=1)
        poll_is_dynamic = serializers.BooleanField()
        area_vote_time_delta = serializers.IntegerField(required=False)
        proposal_time_delta = serializers.IntegerField(required=False)
        prediction_statement_time_delta = serializers.IntegerField(required=False)
        prediction_bet_time_delta = serializers.IntegerField(required=False)
        delegate_vote_time_delta = serializers.IntegerField(required=False)
        vote_time_delta = serializers.IntegerField(required=False)
        end_time_delta = serializers.IntegerField()

    def get(self, request, group_id: int):
        serializer = self.FilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qs = poll_phase_template_list(fetched_by=request.user,
                                      group_id=group_id,
                                      filters=serializer.validated_data)

        return get_paginated_response(pagination_class=LimitOffsetPagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=qs,
                                      request=request,
                                      view=self)


@extend_schema(tags=['poll'])
class PollPhaseTemplateCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        name = serializers.CharField(max_length=255)
        poll_type = serializers.IntegerField(max_value=4, min_value=1)
        poll_is_dynamic = serializers.BooleanField()
        area_vote_time_delta = serializers.IntegerField(required=False)
        proposal_time_delta = serializers.IntegerField(required=False)
        prediction_statement_time_delta = serializers.IntegerField(required=False)
        prediction_bet_time_delta = serializers.IntegerField(required=False)
        delegate_vote_time_delta = serializers.IntegerField(required=False)
        vote_time_delta = serializers.IntegerField(required=False)
        end_time_delta = serializers.IntegerField()

    def post(self, request, group_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        template = poll_phase_template_create(user_id=request.user.id, group_id=group_id, **serializer.validated_data)

        return Response(status=status.HTTP_201_CREATED, data=template.id)


@extend_schema(tags=['poll'])
class PollPhaseTemplateUpdateAPI(APIView):
    def post(self, request, template_id: int):
        serializer = PollPhaseTemplateCreateAPI.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        poll_phase_template_update(user_id=request.user.id, template_id=template_id, data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll'])
class PollPhaseTemplateDeleteAPI(APIView):
    def post(self, request, template_id: int):
        poll_phase_template_delete(user_id=request.user.id, template_id=template_id)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['poll'], description=Poll.notification_docs())
class PollNotificationSubscribeAPI(NotificationSubscribeTemplateAPI):
    lazy_action = poll_notification_subscribe
