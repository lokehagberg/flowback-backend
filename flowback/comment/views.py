# Create your views here.
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.comment.selectors import comment_list
from flowback.comment.services import comment_create, comment_update, comment_delete
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response


class CommentListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 20
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        order_by = serializers.CharField(required=False)
        id = serializers.IntegerField(required=False)
        author_id = serializers.IntegerField(required=False)
        parent_id = serializers.IntegerField(required=False)
        score__gt = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.Serializer):
        class FileSerializer(serializers.Serializer):  # TODO why is it updated_at?
            file = serializers.CharField(source='updated_at')

        id = serializers.IntegerField()
        author_id = serializers.IntegerField()
        author_name = serializers.CharField(source='author.username')
        author_profile_image = serializers.ImageField(source='author.profile_image')
        parent_id = serializers.IntegerField(allow_null=True)
        created_at = serializers.DateTimeField()
        edited = serializers.BooleanField()
        active = serializers.BooleanField()
        message = serializers.CharField()
        attachments = FileSerializer(source="attachments.filesegment_set", many=True, allow_null=True)
        score = serializers.IntegerField()

    def get(self, request, comment_section_id: int):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        comments = comment_list(comment_section_id=comment_section_id,
                                filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=comments,
                                      request=request,
                                      view=self)


class CommentCreateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        parent_id = serializers.IntegerField(required=False)
        message = serializers.CharField()
        attachments = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)

    def post(self, request, comment_section_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = comment_create(comment_section_id=comment_section_id, author_id=request.user.id,
                                 **serializer.validated_data)

        return Response(status=status.HTTP_200_OK, data=comment.id)


class CommentUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        message = serializers.CharField()

    def post(self, request, comment_section_id: int, comment_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment_update(comment_section_id=comment_section_id, comment_id=comment_id,
                       fetched_by=request.user.id, data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class CommentDeleteAPI(APIView):
    def post(self, request, comment_section_id: int, comment_id: int):
        comment_delete(fetched_by=request.user, comment_section_id=comment_section_id,
                       comment_id=comment_id)

        return Response(status=status.HTTP_200_OK)
