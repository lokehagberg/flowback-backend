from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.user.models import OnboardUser, User
from flowback.user.selectors import get_user, user_list
from flowback.user.services import (user_create, user_create_verify, user_forgot_password,
                                    user_forgot_password_verify, user_update, user_delete, user_get_chat_channel)


class UserCreateApi(APIView):
    permission_classes = [AllowAny]

    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = OnboardUser
            fields = 'username', 'email'

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_create(**serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class UserCreateVerifyApi(APIView):
    permission_classes = [AllowAny]

    class InputSerializer(serializers.Serializer):
        verification_code = serializers.UUIDField()
        password = serializers.CharField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_create_verify(**serializer.validated_data)

        return Response(status=status.HTTP_201_CREATED)


class UserForgotPasswordApi(APIView):
    permission_classes = [AllowAny]

    class InputSerializer(serializers.Serializer):
        email = serializers.EmailField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_forgot_password(**serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class UserForgotPasswordVerifyApi(APIView):
    permission_classes = [AllowAny]

    class InputSerializer(serializers.Serializer):
        verification_code = serializers.UUIDField()
        password = serializers.CharField()

    def post(self, request):
        serializers = self.InputSerializer(data=request.data)
        serializers.is_valid(raise_exception=True)

        user_forgot_password_verify(**serializers.validated_data)

        return Response(status=status.HTTP_200_OK)


class UserListApi(APIView):
    class Pagination(LimitOffsetPagination):
        default_limit = 1
        max_limit = 1000

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        username = serializers.CharField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = 'id', 'username', 'profile_image', \
                     'banner_image', 'bio', 'website'

    def get(self, request):
        filter_serializer = self.FilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)

        users = user_list(fetched_by=request.user, filters=filter_serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=users,
                                      request=self.request,
                                      view=self)


class UserGetApi(APIView):
    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = 'id', 'email', 'username', 'profile_image', \
                     'banner_image', 'bio', 'website', 'dark_theme'

    def get(self, request):
        user = get_user(request.user.id)
        serializer = self.OutputSerializer(user)
        return Response(serializer.data)


class UserUpdateApi(APIView):
    class InputSerializer(serializers.ModelSerializer):
        username = serializers.CharField(required=False)
        profile_image = serializers.ImageField(required=False)
        banner_image = serializers.ImageField(required=False)
        bio = serializers.CharField(required=False)
        website = serializers.CharField(required=False)

        class Meta:
            model = User
            fields = 'username', 'profile_image', 'banner_image', 'bio', 'website', 'dark_theme'

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_update(user=request.user, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class UserDeleteAPI(APIView):
    def post(self, request):
        user_delete(user_id=request.user.id)

        return Response(status=status.HTTP_200_OK)


class UserGetChatChannelAPI(APIView):
    class FilterSerializer(serializers.Serializer):
        target_user_ids = serializers.ListField(child=serializers.IntegerField())

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        title = serializers.CharField()

    def get(self, request):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = user_get_chat_channel(user_id=request.user.id, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK, data=self.OutputSerializer(data).data)
