from django.shortcuts import render

# Create your views here.
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView, Response

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.common.services import get_object
from flowback.group.serializers import GroupUserSerializer
from flowback.poll.models import Poll, PollProposal, PollVotingTypeRanking, PollVotingTypeForAgainst
from .selectors.poll import poll_list
from .selectors.prediction import poll_prediction_statement_list, poll_prediction_list
from .selectors.proposal import poll_proposal_list, poll_user_schedule_list
from .selectors.vote import poll_vote_list, poll_delegates_list, delegate_poll_vote_list
from .selectors.comment import poll_comment_list

from .services.comment import poll_comment_create, poll_comment_update, poll_comment_delete
from .services.poll import poll_create, poll_update, poll_delete, poll_refresh_cheap, poll_notification, \
    poll_notification_subscribe
from .services.prediction import poll_prediction_statement_create, poll_prediction_statement_delete, \
    poll_prediction_create, poll_prediction_update, poll_prediction_delete, poll_prediction_statement_vote_create, \
    poll_prediction_statement_vote_update, poll_prediction_statement_vote_delete
from .services.proposal import poll_proposal_create, poll_proposal_delete
from .services.vote import poll_proposal_vote_update, poll_proposal_delegate_vote_update

from flowback.comment.views import CommentListAPI, CommentCreateAPI, CommentUpdateAPI, CommentDeleteAPI


class PollListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        id_list = serializers.ListField(child=serializers.IntegerField(), required=False)
        order_by = serializers.CharField(default='created_at_desc')
        pinned = serializers.NullBooleanField(required=False, default=None)

        title = serializers.CharField(required=False)
        title__icontains = serializers.CharField(required=False)
        poll_type = serializers.ChoiceField((0, 1, 2), required=False)
        tag = serializers.IntegerField(required=False)
        tag_name = serializers.CharField(required=False)
        tag_name__icontains = serializers.CharField(required=False)
        status = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        created_by = GroupUserSerializer()
        group_joined = serializers.BooleanField(required=False)
        group_id = serializers.IntegerField(source='created_by.group_id')
        group_name = serializers.CharField(source='created_by.group.name')
        group_image = serializers.ImageField(source='created_by.group.image')
        tag_name = serializers.CharField(source='tag.tag_name')
        hide_poll_users = serializers.BooleanField(source='created_by.group.hide_poll_users')
        total_comments = serializers.IntegerField()

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
                      'vote_start_date',
                      'delegate_vote_end_date',
                      'end_date',
                      'result',
                      'participants',
                      'pinned',
                      'dynamic',
                      'total_comments',
                      'quorum',
                      'status')

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
            proposal_created_by_name = serializers.IntegerField(source='proposal.created_by.user.username')
            priority = serializers.IntegerField()
            score = serializers.IntegerField()

            class Meta:
                ordering = ['priority']

        class VoteCardinalOutputSerializer(serializers.Serializer):
            proposal_id = serializers.IntegerField()
            proposal_title = serializers.CharField(source='proposal.title')
            proposal_created_by_id = serializers.IntegerField(source='proposal.created_by.user_id')
            proposal_created_by_name = serializers.IntegerField(source='proposal.created_by.user.username')
            score = serializers.IntegerField()

            class Meta:
                ordering = ['priority']

        class VoteForAgainstOutputSerializer(serializers.Serializer):
            proposal_id = serializers.IntegerField()
            proposal_title = serializers.CharField(source='proposal.title')
            proposal_created_by_id = serializers.IntegerField(source='proposal.created_by.user_id')
            proposal_created_by_name = serializers.IntegerField(source='proposal.created_by.user.username')
            score = serializers.IntegerField()
            total_delegators = serializers.IntegerField()

            class Meta:
                ordering = ['vote']

        def get_vote(self, obj):
            if hasattr(obj, 'poll_voting_type_ranking'):
                return self.VoteRankingOutputSerializer

            elif hasattr(obj, 'poll_voting_type_for_against'):
                return self.VoteForAgainstOutputSerializer

            elif hasattr(obj, 'poll_voting_type_for_cardinal'):
                return self.VoteCardinalOutputSerializer

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


class PollNotificationSubscribeApi(APIView):
    class InputSerializer(serializers.Serializer):
        categories = serializers.MultipleChoiceField(choices=poll_notification.possible_categories)

    def post(self, request, poll: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_notification_subscribe(user_id=request.user.id, poll_id=poll, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)



class PollCreateAPI(APIView):
    class InputSerializer(serializers.ModelSerializer):
        tag = serializers.IntegerField()
        quorum = serializers.IntegerField(required=False)
        public = serializers.BooleanField(default=False)

        class Meta:
            model = Poll
            fields = ('title', 'description', 'start_date', 'proposal_end_date', 'vote_start_date',
                      'delegate_vote_end_date', 'end_date', 'poll_type', 'public', 'tag', 'pinned', 'dynamic', 'quorum')

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll = poll_create(user_id=request.user.id, group_id=group, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=poll.id)


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


class PollDeleteAPI(APIView):
    def post(self, request, poll: int):
        poll_refresh_cheap(poll_id=poll)  # TODO get celery
        poll_delete(user_id=request.user.id, poll_id=poll)
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

    def get(self, request, poll: int = None):
        poll = get_object(Poll, id=poll)
        if poll.poll_type == Poll.PollType.RANKING:
            filter_serializer = self.FilterSerializer(data=request.query_params)
            output_serializer = self.OutputSerializer

        else:
            filter_serializer = self.FilterSerializerTypeSchedule(data=request.query_params)
            output_serializer = self.OutputSerializerTypeSchedule

        filter_serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll.id)  # TODO get celery
        proposals = poll_proposal_list(fetched_by=request.user, poll_id=poll.id,
                                       filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=output_serializer,
            queryset=proposals,
            request=request,
            view=self
        )


# TODO Redundant API, request removal
class PollUserScheduleListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10
        max_limit = 500

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        poll_title = serializers.CharField(required=False)
        poll_title__icontains = serializers.CharField(required=False)
        start_date = serializers.DateTimeField(required=False)
        end_date = serializers.DateTimeField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        created_by = GroupUserSerializer()
        hide_poll_users = serializers.BooleanField(source='created_by.group.hide_poll_users')
        group_id = serializers.IntegerField(source='created_by.group_id')
        title = serializers.CharField(source='poll.title')
        description = serializers.CharField(source='poll.description')
        start_date = serializers.DateTimeField(source='pollproposaltypeschedule.start_date')
        end_date = serializers.DateTimeField(source='pollproposaltypeschedule.end_date')

        class Meta:
            model = PollProposal
            fields = ('group_id',
                      'id',
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

    def post(self, request, poll: int):
        poll = get_object(Poll, id=poll)
        if poll.poll_type == Poll.PollType.SCHEDULE:
            serializer = self.InputSerializerSchedule(data=request.data)

        else:
            serializer = self.InputSerializerDefault(data=request.data)

        serializer.is_valid(raise_exception=True)
        poll_refresh_cheap(poll_id=poll.id)  # TODO get celery
        proposal = poll_proposal_create(user_id=request.user.id, poll_id=poll.id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=proposal.id)


class PollProposalDeleteAPI(APIView):
    def post(self, request, proposal: int):
        poll_proposal_delete(user_id=request.user.id, proposal_id=proposal)
        return Response(status=status.HTTP_200_OK)


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
            model = PollVotingTypeRanking
            fields = ('author',
                      'author_delegate',
                      'proposal',
                      'score')

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


# TODO change serializer based upon poll type
class PollProposalVoteUpdateAPI(APIView):
    # For Ranking, Schedule
    class InputSerializerDefault(serializers.Serializer):
        votes = serializers.ListField(child=serializers.IntegerField())

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
        poll_refresh_cheap(poll_id=poll)  # TODO get celery
        poll_proposal_vote_update(user_id=request.user.id, poll_id=poll, data=serializer.validated_data)
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


# TODO change serializer based upon poll type
class PollProposalDelegateVoteUpdateAPI(APIView):
    # For Ranking, Schedule
    class InputSerializerDefault(serializers.Serializer):
        votes = serializers.ListField(child=serializers.IntegerField())

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
        poll_refresh_cheap(poll_id=poll)  # TODO get celery
        poll_proposal_delegate_vote_update(user_id=request.user.id, poll_id=poll, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class PollCommentListAPI(CommentListAPI):
    def get(self, request, poll: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        comments = poll_comment_list(fetched_by=request.user, poll_id=poll, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=comments,
                                      request=request,
                                      view=self)


class PollCommentCreateAPI(CommentCreateAPI):
    def post(self, request, poll: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = poll_comment_create(author_id=request.user.id, poll_id=poll, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK, data=comment.id)


class PollCommentUpdateAPI(CommentUpdateAPI):
    def post(self, request, poll: int, comment_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        poll_comment_update(fetched_by=request.user.id,
                            poll_id=poll,
                            comment_id=comment_id,
                            data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class PollCommentDeleteAPI(CommentDeleteAPI):
    def post(self, request, poll: int, comment_id: int):
        poll_comment_delete(fetched_by=request.user.id, poll_id=poll, comment_id=comment_id)

        return Response(status=status.HTTP_200_OK)


class PollPredictionStatementListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 100
        default_limit = 25

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        poll_id = serializers.IntegerField(required=False)
        proposals = serializers.ListField(required=False, child=serializers.IntegerField())
        description = serializers.CharField(required=False)
        created_by_id = serializers.IntegerField(required=False)
        user_prediction_exists = serializers.BooleanField(required=False)
        user_vote_exists = serializers.BooleanField(required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        poll_id = serializers.IntegerField()
        proposals = serializers.ListField(source='pollpredictionstatementsegment_id',
                                          child=serializers.IntegerField())
        description = serializers.CharField()
        created_by = GroupUserSerializer()
        user_prediction = serializers.IntegerField(source='user_prediction__score', required=False)
        user_vote = serializers.BooleanField(source='user_vote__vote', required=False)

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


class PollPredictionListAPI(APIView):
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
        score = serializers.IntegerField()

    def get(self, request, group_id: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        predictions = poll_prediction_list(fetched_by=request.user,
                                           group_id=group_id,
                                           filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=predictions,
            request=request,
            view=self
        )


class PollPredictionStatementCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        class SegmentSerializer(serializers.Serializer):
            proposal_id = serializers.IntegerField()
            is_true = serializers.BooleanField()

        description = serializers.CharField()
        end_date = serializers.DateTimeField()
        segments = SegmentSerializer(many=True)

    def post(self, request, poll_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created_id = poll_prediction_statement_create(poll=poll_id,
                                                      user=request.user,
                                                      **serializer.validated_data)

        return Response(created_id, status=status.HTTP_201_CREATED)


class PollPredictionStatementDeleteAPI(APIView):
    def post(self, request, prediction_statement_id: int):
        poll_prediction_statement_delete(user=request.user,
                                         prediction_statement_id=prediction_statement_id)

        return Response(status=status.HTTP_200_OK)


class PollPredictionCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        score = serializers.IntegerField()

    def post(self, request, prediction_statement_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        created_id = poll_prediction_create(user=request.user,
                                            prediction_statement_id=prediction_statement_id,
                                            **serializer.validated_data)

        return Response(created_id, status=status.HTTP_201_CREATED)


class PollPredictionUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        score = serializers.IntegerField()

    def post(self, request, prediction_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        poll_prediction_update(user=request.user, prediction_id=prediction_id, data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class PollPredictionDeleteAPI(APIView):
    def post(self, request, prediction_id: int):
        poll_prediction_delete(user=request.user, prediction_id=prediction_id)

        return Response(status=status.HTTP_200_OK)


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


class PollPredictionStatementVoteUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        vote = serializers.BooleanField()

    def post(self, request, prediction_statement_vote_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_prediction_statement_vote_update(user=request.user,
                                              prediction_statement_vote_id=prediction_statement_vote_id,
                                              data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class PollPredictionStatementVoteDeleteAPI(APIView):
    def post(self, request, prediction_statement_vote_id: int):
        poll_prediction_statement_vote_delete(user=request.user,
                                              prediction_statement_vote_id=prediction_statement_vote_id)

        return Response(status=status.HTTP_200_OK)
