from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response

from flowback.group.models import GroupTags
from flowback.group.selectors import group_tags_list
from flowback.group.services import group_tag_create, group_tag_update, group_tag_delete


class GroupTagsListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 1

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        tag_name = serializers.CharField(required=False)
        tag_name__icontains = serializers.CharField(required=False)
        active = serializers.BooleanField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = GroupTags
            fields = ('id', 'tag_name', 'active')

    def get(self, request, group: int):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        tags = group_tags_list(group=group,
                               fetched_by=request.user,
                               filters=filter_serializer.validated_data)

        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=tags,
            request=request,
            view=self
        )


class GroupTagsCreateApi(APIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = GroupTags
            fields = ('tag_name',)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        group_tag_create(user=request.user.id, group=group, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class GroupTagsUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        tag = serializers.IntegerField(source='id')
        active = serializers.BooleanField(required=False)

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tag = serializer.validated_data.pop('tag')

        group_tag_update(user=request.user.id, group=group, tag=tag, data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class GroupTagsDeleteApi(APIView):
    class InputSerializer(serializers.Serializer):
        tag = serializers.IntegerField()

    def post(self, request, group: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tag = serializer.validated_data.pop('tag')

        group_tag_delete(user=request.user.id, group=group, tag=tag)

        return Response(status=status.HTTP_200_OK)
