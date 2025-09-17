from django.shortcuts import render

# Create your views here.
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView, Response

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.common.services import get_object
from flowback.poll.models import Poll, PollProposal, PollVotingTypeRanking, PollVotingTypeForAgainst
from flowback.poll.selectors import poll_list, poll_proposal_list, poll_vote_list, poll_delegates_list, \
    poll_user_schedule_list
from flowback.poll.services import poll_create, poll_update, poll_delete, poll_proposal_create, poll_proposal_delete, \
    poll_proposal_vote_update, poll_proposal_delegate_vote_update, poll_refresh_cheap


class PollListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        created_by = serializers.IntegerField(required=False)
        title = serializers.CharField(required=False)
        title__icontains = serializers.CharField(required=False)
        poll_type = serializers.ChoiceField((0, 1, 2), required=False)
        tag = serializers.IntegerField(required=False)
        tag_name = serializers.CharField(required=False)
        tag_name__icontains = serializers.CharField(required=False)
        finished = serializers.NullBooleanField(required=False, default=None)

    class OutputSerializer(serializers.ModelSerializer):
        tag_name = serializers.CharField(source='tag.tag_name')

        class Meta:
            model = Poll
            fields = ('id',
                      'created_by',
                      'title',
                      'description',
                      'poll_type',
                      'public',
                      'tag',
                      'tag_name',
                      'start_date',
                      'end_date',
                      'finished',
                      'result',
                      'participants',
                      'dynamic')

    def get(self, request, group: int = None):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        polls = poll_list(fetched_by=request.user, group_id=group, filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=polls,
            request=request,
            view=self
        )


class PollCreateAPI(APIView):
    class InputSerializer(serializers.ModelSerializer):
        tag = serializers.IntegerField()
        public = serializers.BooleanField(default=False)

        class Meta:
            model = Poll
            fields = ('title', 'description', 'start_date', 'end_date', 'poll_type', 'public', 'tag', 'dynamic')

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll = poll_create(user_id=request.user.id, group_id=group, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=poll.id)


class PollUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        title = serializers.CharField(required=False)
        description = serializers.CharField(required=False)

    def post(self, request, group: int, poll: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll)  # TODO get celery
        poll_update(user_id=request.user.id, group_id=group, poll_id=poll, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class PollDeleteAPI(APIView):
    def post(self, request, group: int, poll: int):
        poll_refresh_cheap(poll_id=poll)  # TODO get celery
        poll_delete(user_id=request.user.id, group_id=group, poll_id=poll)
        return Response(status=status.HTTP_200_OK)


class PollProposalListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        created_by = serializers.IntegerField(required=False)
        title = serializers.CharField(required=False)
        title__icontains = serializers.CharField(required=False)

    class FilterSerializerTypeSchedule(FilterSerializer):
        start_date = serializers.DateTimeField(required=False)
        end_date = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = PollProposal
            fields = ('id',
                      'created_by',
                      'poll',
                      'title',
                      'description',
                      'score')

    class OutputSerializerTypeSchedule(OutputSerializer):
        start_date = serializers.DateTimeField(source='pollproposaltypeschedule.start_date')
        end_date = serializers.DateTimeField(source='pollproposaltypeschedule.end_date')

        class Meta:
            model = PollProposal
            fields = ('id',
                      'created_by',
                      'poll',
                      'score',
                      'start_date',
                      'end_date')

    def get(self, request, group: int = None, poll: int = None):
        poll = get_object(Poll, id=poll)
        if poll.poll_type == Poll.PollType.RANKING:
            filter_serializer = self.FilterSerializer(data=request.query_params)
            output_serializer = self.OutputSerializer

        else:
            filter_serializer = self.FilterSerializerTypeSchedule(data=request.query_params)
            output_serializer = self.OutputSerializerTypeSchedule

        filter_serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll.id)  # TODO get celery
        proposals = poll_proposal_list(fetched_by=request.user, group_id=group, poll_id=poll.id,
                                       filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=output_serializer,
            queryset=proposals,
            request=request,
            view=self
        )


class PollUserScheduleListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10
        max_limit = 500

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        created_by = serializers.IntegerField(required=False)
        poll_title = serializers.CharField(required=False)
        poll_title__icontains = serializers.CharField(required=False)
        start_date = serializers.DateTimeField(required=False)
        end_date = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        title = serializers.CharField(source='poll.title')
        description = serializers.CharField(source='poll.description')
        start_date = serializers.DateTimeField(source='pollproposaltypeschedule.start_date')
        end_date = serializers.DateTimeField(source='pollproposaltypeschedule.end_date')

        class Meta:
            model = PollProposal
            fields = ('id',
                      'created_by',
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


class PollProposalCreateAPI(APIView):
    class InputSerializerDefault(serializers.ModelSerializer):
        class Meta:
            model = PollProposal
            fields = ('title', 'description')

    class InputSerializerSchedule(serializers.ModelSerializer):
        start_date = serializers.DateTimeField()
        end_date = serializers.DateTimeField()

        def validate(self, data):
            if data.get('start_date') >= data.get('end_date'):
                raise ValidationError('Start date can\'t be the same or later than End date')

            return data

        class Meta:
            model = PollProposal
            fields = ('title', 'description', 'start_date', 'end_date')

    def post(self, request, group: int, poll: int):
        poll = get_object(Poll, id=poll)
        if poll.poll_type == Poll.PollType.SCHEDULE:
            serializer = self.InputSerializerSchedule(data=request.data)

        else:
            serializer = self.InputSerializerDefault(data=request.data)

        serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll.id)  # TODO get celery
        proposal = poll_proposal_create(user_id=request.user.id, group_id=group, poll_id=poll.id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=proposal.id)


class PollProposalDeleteAPI(APIView):
    def post(self, request, group: int, poll: int, proposal: int):
        poll_refresh_cheap(poll_id=poll)  # TODO get celery
        poll_proposal_delete(user_id=request.user.id, group_id=group, poll_id=poll, proposal_id=proposal)
        return Response(status=status.HTTP_200_OK)


class PollProposalVoteListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        delegates = serializers.BooleanField(required=False, default=False)
        delegate_pool_id = serializers.IntegerField(required=False)
        delegate_user_id = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = PollVotingTypeRanking
            fields = ('author',
                      'author_delegate',
                      'proposal',
                      'priority',
                      'score')

    class OutputSerializerTypeForAgainst(serializers.ModelSerializer):
        class Meta:
            model = PollVotingTypeForAgainst
            fields = ('author',
                      'author_delegate',
                      'proposal',
                      'vote',
                      'score')

    def get(self, request, group: int, poll: int):
        poll = get_object(Poll, id=poll)
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        delegates = filter_serializer.validated_data.pop('delegates')
        poll_refresh_cheap(poll_id=poll.id)  # TODO get celery

        votes = poll_vote_list(fetched_by=request.user, group_id=group, poll_id=poll.id,
                               delegates=delegates,
                               filters=filter_serializer.validated_data)

        if poll.poll_type == Poll.PollType.SCHEDULE:
            output_serializer = self.OutputSerializerTypeForAgainst
        elif poll.poll_type == Poll.PollType.RANKING:
            output_serializer = self.OutputSerializer
        else:
            raise ValidationError('Unknown poll type')

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=output_serializer,
            queryset=votes,
            request=request,
            view=self
        )


# TODO change serializer based upon poll type
class PollProposalVoteUpdateAPI(APIView):
    # For Ranking, Schedule
    class InputSerializerDefault(serializers.Serializer):
        votes = serializers.ListField(child=serializers.IntegerField())

    def post(self, request, group: int, poll: int):
        serializer = self.InputSerializerDefault(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll)  # TODO get celery
        poll_proposal_vote_update(user_id=request.user.id, group_id=group, poll_id=poll, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class PollDelegatesListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        created_by = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = PollProposal
            fields = ('created_by',)

    def get(self, request, group: int, poll: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll)  # TODO get celery

        delegates = poll_delegates_list(fetched_by=request.user, group_id=group, poll_id=poll,
                                        filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=delegates,
            request=request,
            view=self
        )


# TODO change serializer based upon poll type
class PollProposalDelegateVoteUpdateAPI(APIView):
    # For Ranking, Schedule
    class InputSerializerDefault(serializers.Serializer):
        votes = serializers.ListField(child=serializers.IntegerField())

    def post(self, request, group: int, poll: int):
        serializer = self.InputSerializerDefault(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll)  # TODO get celery
        poll_proposal_delegate_vote_update(user_id=request.user.id, group_id=group,
                                           poll_id=poll, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)
