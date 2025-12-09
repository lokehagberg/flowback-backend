from drf_spectacular.utils import extend_schema

from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView, Response

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.common.services import get_object
from flowback.poll.models import Poll, PollProposal

from ..selectors.proposal import poll_proposal_list
from ..serializers import PollProposalSerializer
from ..services.proposal import poll_proposal_create, poll_proposal_delete
from ...files.serializers import FileCollectionCreateSerializerMixin


# TODO check alternative solution for schedule
@extend_schema(tags=['poll/proposal'])
class PollProposalListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 10

    class FilterSerializer(serializers.Serializer):
        order_by = serializers.ChoiceField(required=False,
                                           default='created_at_desc',
                                           choices=['created_at_asc', 'created_at_desc',
                                                    'score_asc', 'score_desc'])
        id = serializers.IntegerField(required=False)
        created_by_user_id_list = serializers.CharField(required=False)
        title = serializers.CharField(required=False)
        title__icontains = serializers.CharField(required=False)
        has_attachments = serializers.BooleanField(required=False, allow_null=True, default=None)
        start_date = serializers.DateTimeField(required=False)
        end_date = serializers.DateTimeField(required=False)

    class OutputSerializer(PollProposalSerializer):
        pass

    def get(self, request, poll: int = None):
        poll = get_object(Poll, id=poll)
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        proposals = poll_proposal_list(fetched_by=request.user, poll_id=poll.id,
                                       filters=serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=proposals,
            request=request,
            view=self)


@extend_schema(tags=['poll/proposal'])
class PollProposalCreateAPI(APIView):
    class InputSerializerDefault(serializers.ModelSerializer, FileCollectionCreateSerializerMixin):

        class Meta:
            model = PollProposal
            fields = ('title', 'description', 'attachments', 'blockchain_id')

    class InputSerializerSchedule(serializers.ModelSerializer, FileCollectionCreateSerializerMixin):
        start_date = serializers.DateTimeField()
        end_date = serializers.DateTimeField()

        def validate(self, data):
            if data.get('start_date') >= data.get('end_date'):
                raise ValidationError('Start date can\'t be the same or later than End date')

            return data

        class Meta:
            model = PollProposal
            fields = ('title', 'description', 'blockchain_id', 'attachments', 'start_date', 'end_date')

    def post(self, request, poll: int):
        poll = get_object(Poll, id=poll)
        if poll.poll_type == Poll.PollType.SCHEDULE:
            serializer = self.InputSerializerSchedule(data=request.data)

        else:
            serializer = self.InputSerializerDefault(data=request.data)

        serializer.is_valid(raise_exception=True)
        proposal = poll_proposal_create(user_id=request.user.id, poll_id=poll.id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK, data=proposal.id)


@extend_schema(tags=['poll/proposal'])
class PollProposalDeleteAPI(APIView):
    def post(self, request, proposal: int):
        poll_proposal_delete(user_id=request.user.id, proposal_id=proposal)
        return Response(status=status.HTTP_200_OK)

