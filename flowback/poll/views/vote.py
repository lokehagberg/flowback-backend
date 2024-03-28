from drf_spectacular.utils import extend_schema

from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView, Response

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.common.services import get_object

from flowback.poll.models import Poll, PollVotingTypeRanking, PollVotingTypeForAgainst, PollVotingTypeCardinal

from ..selectors.vote import poll_vote_list, delegate_poll_vote_list
from ..services.poll import poll_refresh_cheap
from ..services.vote import poll_proposal_vote_update, poll_proposal_delegate_vote_update, poll_vote


@extend_schema(tags=['poll'])
class PollProposalVoteListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        delegates = serializers.BooleanField(required=False, default=False)
        delegate_pool_id = serializers.IntegerField(required=False)
        delegate_user_id = serializers.IntegerField(required=False)

    class OutputSerializerTypeRanking(serializers.ModelSerializer):
        class Meta:
            model = PollVotingTypeRanking
            fields = ('author',
                      'author_delegate',
                      'proposal',
                      'priority',
                      'score')

    class OutputSerializerTypeCardinal(serializers.ModelSerializer):
        class Meta:
            model = PollVotingTypeCardinal
            fields = ('author',
                      'author_delegate',
                      'proposal',
                      'score',
                      'raw_score')

    class OutputSerializerTypeForAgainst(serializers.ModelSerializer):
        class Meta:
            model = PollVotingTypeForAgainst
            fields = ('author',
                      'author_delegate',
                      'proposal',
                      'vote',
                      'score')

    def get(self, request, poll: int):
        poll = get_object(Poll, id=poll)
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        delegates = filter_serializer.validated_data.pop('delegates')
        poll_refresh_cheap(poll_id=poll.id)  # TODO get celery

        votes = poll_vote_list(fetched_by=request.user, poll_id=poll.id,
                               delegates=delegates,
                               filters=filter_serializer.validated_data)

        if poll.poll_type == Poll.PollType.SCHEDULE:
            output_serializer = self.OutputSerializerTypeForAgainst
        elif poll.poll_type == Poll.PollType.RANKING:
            output_serializer = self.OutputSerializerTypeRanking
        elif poll.poll_type == Poll.PollType.CARDINAL:
            output_serializer = self.OutputSerializerTypeCardinal
        else:
            raise ValidationError('Unknown poll type')

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=output_serializer,
            queryset=votes,
            request=request,
            view=self
        )


# TODO need fixes
class DelegatePollVoteListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 20
        default_limit = 10

    class InputSerializer(serializers.Serializer):
        poll_id = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.Serializer):
        poll_id = serializers.IntegerField()
        poll_title = serializers.CharField(source='poll.title')
        vote = serializers.SerializerMethodField()

        class VoteRankingOutputSerializer(serializers.Serializer):
            proposal_id = serializers.IntegerField()
            proposal_title = serializers.CharField(source='proposal.title')
            proposal_created_by_id = serializers.IntegerField(source='proposal.created_by.user_id')
            proposal_created_by_name = serializers.CharField(source='proposal.created_by.user.username')
            priority = serializers.IntegerField()
            score = serializers.IntegerField()

            class Meta:
                ordering = ['priority']

        class VoteCardinalOutputSerializer(serializers.Serializer):
            proposal_id = serializers.IntegerField()
            proposal_title = serializers.CharField(source='proposal.title')
            proposal_created_by_id = serializers.IntegerField(source='proposal.created_by.user_id')
            proposal_created_by_name = serializers.CharField(source='proposal.created_by.user.username')
            score = serializers.IntegerField(allow_null=True)
            raw_score = serializers.IntegerField()

            class Meta:
                ordering = ['priority']

        class VoteForAgainstOutputSerializer(serializers.Serializer):
            proposal_id = serializers.IntegerField()
            proposal_title = serializers.CharField(source='proposal.title')
            proposal_created_by_id = serializers.IntegerField(source='proposal.created_by.user_id')
            proposal_created_by_name = serializers.CharField(source='proposal.created_by.user.username')
            score = serializers.IntegerField()
            total_delegators = serializers.IntegerField()

            class Meta:
                ordering = ['vote']

        def get_vote(self, obj):
            poll_type = obj.poll.poll_type

            if poll_type == Poll.PollType.RANKING:
                serializer = self.VoteRankingOutputSerializer(obj.pollvotingtyperanking_set,
                                                              many=True,
                                                              allow_null=True,
                                                              required=False)

                return serializer.data

            elif poll_type == Poll.PollType.FOR_AGAINST:
                serializer = self.VoteForAgainstOutputSerializer(obj.pollvotingtypeforagainst_set,
                                                                 many=True,
                                                                 allow_null=True,
                                                                 required=False)

                return serializer.data

            elif poll_type == Poll.PollType.CARDINAL:
                serializer = self.VoteCardinalOutputSerializer(obj.pollvotingtypecardinal_set,
                                                               many=True,
                                                               allow_null=True,
                                                               required=False)

                return serializer.data

            else:
                return None

    def get(self, request, delegate_pool_id: int):
        serializer = self.InputSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        votes = delegate_poll_vote_list(fetched_by=request.user,
                                        delegate_pool_id=delegate_pool_id,
                                        filters=serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=votes,
            request=request,
            view=self
        )


# TODO change serializer based upon poll type
@extend_schema(tags=['poll'])
class PollProposalVoteUpdateAPI(APIView):
    # For Ranking, Schedule
    class InputSerializerDefault(serializers.Serializer):
        proposals = serializers.ListField(child=serializers.IntegerField())

    class InputSerializerCardinal(serializers.Serializer):
        proposals = serializers.ListField(child=serializers.IntegerField())
        scores = serializers.ListField(child=serializers.IntegerField())

    def post(self, request, poll: int):
        poll = get_object(Poll, id=poll)

        if poll.poll_type in (Poll.PollType.SCHEDULE, Poll.PollType.RANKING):
            input_serializer = self.InputSerializerDefault
        elif poll.poll_type == Poll.PollType.CARDINAL:
            input_serializer = self.InputSerializerCardinal
        else:
            raise ValidationError('Unknown poll type')

        serializer = input_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll.id)  # TODO get celery
        poll_proposal_vote_update(user_id=request.user.id, poll_id=poll.id, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


# TODO change serializer based upon poll type
@extend_schema(tags=['poll'])
class PollProposalDelegateVoteUpdateAPI(APIView):
    # For Ranking, Schedule
    class InputSerializerDefault(serializers.Serializer):
        votes = serializers.ListField(child=serializers.IntegerField())

    class InputSerializerRanking(serializers.Serializer):
        proposals = serializers.ListField(child=serializers.IntegerField())

    class InputSerializerCardinal(serializers.Serializer):
        proposals = serializers.ListField(child=serializers.IntegerField())
        scores = serializers.ListField(child=serializers.IntegerField())

    def post(self, request, poll: int):
        poll = get_object(Poll, id=poll)

        if poll.poll_type == Poll.PollType.SCHEDULE:
            input_serializer = self.InputSerializerDefault
        elif poll.poll_type == Poll.PollType.RANKING:
            input_serializer = self.InputSerializerRanking
        elif poll.poll_type == Poll.PollType.CARDINAL:
            input_serializer = self.InputSerializerCardinal
        else:
            raise ValidationError('Unknown poll type')

        serializer = input_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll.id)  # TODO get celery
        poll_proposal_delegate_vote_update(user_id=request.user.id, poll_id=poll.id, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class PollVoteUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        score = serializers.IntegerField(min_value=-1, max_value=1)

    def post(self, request, poll_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        poll_vote(user_id=request.user.id, poll_id=poll_id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)
