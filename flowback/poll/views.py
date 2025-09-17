from django.shortcuts import render

# Create your views here.
from rest_framework import serializers, status
from rest_framework.views import APIView, Response

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.poll.models import Poll
from flowback.poll.selectors import poll_list
from flowback.poll.services import poll_create, poll_update, poll_delete


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
                      'tag',
                      'tag_name',
                      'start_date',
                      'end_date',
                      'finished',
                      'result',
                      'participants',
                      'dynamic')

    def get(self, request, group: int):
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

        class Meta:
            model = Poll
            fields = ('title', 'description', 'start_date', 'end_date', 'poll_type', 'tag', 'dynamic')

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_create(user_id=request.user.id, group_id=group, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class PollUpdateAPI(APIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Poll
            fields = ('title', 'description')

    def post(self, request, group: int, poll_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll_update(user_id=request.user.id, group_id=group, poll_id=poll_id, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class PollDeleteAPI(APIView):
    def post(self, request, group: int, poll_id: int):
        poll_delete(user_id=request.user.id, group_id=group, poll_id=poll_id)
        return Response(status=status.HTTP_200_OK)
