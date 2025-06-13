from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response

from flowback.group.models import GroupTags
from flowback.group.selectors.tags import group_tags_list
from flowback.group.services.tag import (group_tag_create,
                                         group_tag_update,
                                         group_tag_delete)


@extend_schema(tags=['group/tag'])
class GroupTagsListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 1

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        tag_name = serializers.CharField(required=False)
        tag_name__icontains = serializers.CharField(required=False)
        description = serializers.CharField(required=False)
        description__icontains = serializers.CharField(required=False)
        active = serializers.BooleanField(required=False, default=None, allow_null=True)

    class OutputSerializer(serializers.ModelSerializer):
        imac = serializers.DecimalField(max_digits=9, decimal_places=5, help_text="Interval Mean Absolute Correctness")
        class Meta:
            model = GroupTags
            fields = ('id', 'name', 'description', 'active', 'imac')

    def get(self, request, group_id: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        tags = group_tags_list(group_id=group_id,
                               fetched_by=request.user,
                               filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=tags,
            request=request,
            view=self
        )


@extend_schema(tags=['group/tag'])
class GroupTagsCreateApi(APIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = GroupTags
            fields = ('name', 'description')

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_tag_create(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/tag'])
class GroupTagsUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        tag = serializers.IntegerField()
        description = serializers.CharField(required=False)
        active = serializers.BooleanField(required=False)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tag = serializer.validated_data.pop('tag')

        group_tag_update(user=request.user.id, group=group, tag=tag, data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


@extend_schema(tags=['group/tag'])
class GroupTagsDeleteApi(APIView):
    class InputSerializer(serializers.Serializer):
        tag = serializers.IntegerField()

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tag = serializer.validated_data.pop('tag')

        group_tag_delete(user=request.user.id, group=group, tag=tag)

        return Response(status=status.HTTP_200_OK)
