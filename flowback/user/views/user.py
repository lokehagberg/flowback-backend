from django.contrib.auth import logout
from drf_spectacular.utils import extend_schema
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from tutorial.quickstart.serializers import UserSerializer

from flowback.common.pagination import LimitOffsetPagination, get_paginated_response
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.notification.views import NotificationSubscribeTemplateAPI
from flowback.user.models import OnboardUser, User
from flowback.user.selectors import get_user, user_list, user_chat_invite_list
from flowback.user.serializers import BasicUserSerializer
from flowback.user.services import (user_create, user_create_verify, user_forgot_password,
                                    user_forgot_password_verify, user_update, user_delete, user_get_chat_channel,
                                    user_chat_invite, user_chat_channel_leave, user_chat_channel_update,
                                    user_notification_subscribe)


class UserCreateApi(APIView):
    permission_classes = [AllowAny]

    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = OnboardUser
            fields = 'email'

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_create(**serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class UserCreateVerifyApi(APIView):
    permission_classes = [AllowAny]

    class InputSerializer(serializers.Serializer):
        username = serializers.CharField()
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
        username__icontains = serializers.CharField(required=False)

    class OutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ('id', 'username', 'profile_image',
                      'banner_image', 'public_status', 'chat_status')

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
    class FilterSerializer(serializers.Serializer):
        user_id = serializers.IntegerField(required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        username = serializers.CharField()
        profile_image = serializers.ImageField()
        banner_image = serializers.ImageField()

        bio = serializers.CharField(required=False)
        website = serializers.CharField(required=False)
        contact_email = serializers.CharField(required=False)
        contact_phone = PhoneNumberField(required=False)
        public_status = serializers.BooleanField(required=False)
        chat_status = serializers.BooleanField(required=False)

        email = serializers.CharField(required=False)
        dark_theme = serializers.BooleanField(required=False)
        user_config = serializers.CharField(required=False)

    def get(self, request):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        user = get_user(fetched_by=request.user, **serializer.validated_data)

        serializer = self.OutputSerializer(user)
        return Response(serializer.data)


class UserUpdateApi(APIView):
    class InputSerializer(serializers.Serializer):
        username = serializers.CharField(required=False)
        profile_image = serializers.ImageField(required=False)
        banner_image = serializers.ImageField(required=False)
        bio = serializers.CharField(required=False)
        website = serializers.CharField(required=False)
        dark_theme = serializers.BooleanField(required=False)
        contact_email = serializers.CharField(required=False)
        contact_phone = PhoneNumberField(required=False)
        public_status = serializers.ChoiceField(required=False, choices=User.PublicStatus.choices)
        chat_status = serializers.ChoiceField(required=False, choices=User.PublicStatus.choices)
        email = serializers.CharField(required=False)
        user_config = serializers.CharField(required=False)

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_update(user=request.user, data=serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class UserDeleteAPI(APIView):
    def post(self, request):
        user_delete(user_id=request.user.id)

        return Response(status=status.HTTP_200_OK)


@extend_schema(description=User.notification_docs())
class UserNotificationSubscribeAPI(NotificationSubscribeTemplateAPI):
    lazy_action = user_notification_subscribe


@extend_schema(description="Get/creates a message channel between user(s). "
                           "If there are more than two target_user_ids or the target_user_id has direct_message turned "
                           "into private/(protected and not in same group(s)), it'll create a MessageChannel, "
                           "send/update UserChatInvite(s) to respective users, create/update their "
                           "MessageChannelParticipant active field to False.")
class UserGetChatChannelAPI(APIView):
    class FilterSerializer(serializers.Serializer):
        target_user_ids = serializers.ListField(child=serializers.IntegerField())
        preview = serializers.BooleanField(default=False, help_text="Disabling preview will return 400 if there's no"
                                                                    " MessageChannel found between the users.")

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        title = serializers.CharField()

    def get(self, request):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = user_get_chat_channel(fetched_by=request.user, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK, data=self.OutputSerializer(data).data)


class UserLeaveChatChannelAPI(APIView):
    class InputSerializer(serializers.Serializer):
        message_channel_id = serializers.IntegerField(help_text="You can only leave channels "
                                                                "with the origin_name 'user_group'")

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_chat_channel_leave(user_id=request.user.id, **serializer.validated_data)
        return Response(status=status.HTTP_200_OK)


class UserChatInviteAPI(APIView):
    class InputSerializer(serializers.Serializer):
        invite_id = serializers.IntegerField()
        accept = serializers.BooleanField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_chat_invite(user_id=request.user.id, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class UserChatInviteListAPI(APIView):
    class Pagination(LimitOffsetPagination):
        max_limit = 100

    class FilterSerializer(serializers.Serializer):
        message_channel_id = serializers.IntegerField(required=False)
        rejected = serializers.BooleanField(required=False, allow_null=True)
        rejected__isnull = serializers.BooleanField(required=False, allow_null=True)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        message_channel_name = serializers.CharField(source='message_channel.title')
        message_channel_id = serializers.IntegerField()
        rejected = serializers.BooleanField(allow_null=True)

    def get(self, request):
        serializer = self.FilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        qs = user_chat_invite_list(fetched_by=request.user, filters=serializer.validated_data)

        return get_paginated_response(pagination_class=self.Pagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=qs,
                                      request=self.request,
                                      view=self)


class UserChatChannelUpdateAPI(APIView):
    class InputSerializer(serializers.Serializer):
        channel_id = serializers.IntegerField()
        title = serializers.CharField()

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_chat_channel_update(user_id=request.user.id, **serializer.validated_data)

        return Response(status=status.HTTP_200_OK)


class UserLogoutAPI(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_200_OK)
