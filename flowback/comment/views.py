# Collection of view templates to implement the comment system for other modules
# Do note these views should not be used directly!
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.comment.selectors import comment_list, comment_ancestor_list
from flowback.comment.services import comment_create, comment_update, comment_delete, comment_vote
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from flowback.files.serializers import FileSerializer


class CommentListAPI(APIView):
    lazy_action = comment_list

    class Pagination(LimitOffsetPagination):
        default_limit = 20
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        order_by = serializers.ChoiceField(choices=['created_at_asc',
                                                    'created_at_desc',
                                                    'total_replies_asc',
                                                    'total_replies_desc',
                                                    'score_asc',
                                                    'score_desc'], default='score_desc')
        id = serializers.IntegerField(required=False)
        message__icontains = serializers.ListField(child=serializers.CharField(), required=False)
        author_id = serializers.IntegerField(required=False)
        author_id__in = serializers.CharField(required=False)
        parent_id = serializers.IntegerField(required=False)
        has_attachments = serializers.BooleanField(required=False, allow_null=True, default=None)
        score__gt = serializers.IntegerField(required=False)
        score__lt = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        author_id = serializers.IntegerField()
        author_name = serializers.CharField(source='author.username')
        author_profile_image = serializers.ImageField(source='author.profile_image')
        parent_id = serializers.IntegerField(allow_null=True)
        created_at = serializers.DateTimeField()
        edited = serializers.BooleanField()
        active = serializers.BooleanField()
        message = serializers.CharField(allow_null=True)
        user_vote = serializers.BooleanField(allow_null=True)
        attachments = FileSerializer(source="attachments.filesegment_set", many=True, allow_null=True)
        score = serializers.IntegerField(source='raw_score')

    def get(self, request, *args, **kwargs):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        comments = self.lazy_action.__func__(fetched_by=request.user,
                                             filters=serializer.validated_data,
                                             *args,
                                             **kwargs)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=comments,
                                      request=request,
                                      view=self)


# Returns a list of ancestors to a specific comment
class CommentAncestorListAPI(APIView):
    lazy_action = comment_ancestor_list

    class Pagination(LimitOffsetPagination):
        default_limit = 20
        max_limit = 100

    def get(self, request, *args, **kwargs):
        comments = self.lazy_action.__func__(fetched_by=request.user,
                                             *args,
                                             **kwargs)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=CommentListAPI.OutputSerializer,
                                      queryset=comments,
                                      request=request,
                                      view=self)


class CommentCreateAPI(APIView):
    lazy_action = comment_create

    class InputSerializer(serializers.Serializer):
        parent_id = serializers.IntegerField(required=False)
        message = serializers.CharField(required=False)
        attachments = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = self.lazy_action.__func__(*args,
                                            author_id=request.user.id,
                                            **kwargs,
                                            **serializer.validated_data)

        return Response(status=status.HTTP_200_OK, data=comment.id)


class CommentUpdateAPI(APIView):
    lazy_action = comment_update

    class InputSerializer(serializers.Serializer):
        message = serializers.CharField()

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.lazy_action.__func__(*args,
                                  **kwargs,
                                  fetched_by=request.user.id,
                                  data=serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class CommentDeleteAPI(APIView):
    lazy_action = comment_delete

    def post(self, request, *args, **kwargs):
        self.lazy_action.__func__(*args,
                                  **kwargs,
                                  fetched_by=request.user)

        return Response(status=status.HTTP_200_OK)


class CommentVoteAPI(APIView):
    lazy_action = comment_vote

    class InputSerializer(serializers.Serializer):
        vote = serializers.BooleanField(required=False, allow_null=True)

    def post(self, request, *args, **kwargs):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.lazy_action.__func__(*args,
                                  **kwargs,
                                  **serializer.validated_data,
                                  fetched_by=request.user.id)

        return Response(status=status.HTTP_200_OK)
