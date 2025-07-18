from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.views import APIView

from flowback.common.pagination import get_paginated_response, LimitOffsetPagination
from flowback.server.selectors import reports_list
from flowback.server.services import get_public_config


# Create your views here.
class ServerConfigListAPI(APIView):
    permission_classes = [AllowAny]

    class OutputSerializer(serializers.Serializer):
        DEBUG = serializers.BooleanField(help_text="Backend debug mode")
        FLOWBACK_KANBAN_LANES = serializers.ListField(
            child=serializers.CharField(),
            help_text="List of kanban lanes, when using the kanban list APIs, the kanban lanes represent the position "
                      "of the kanban 'lane' field, starting from 1")
        FLOWBACK_ALLOW_GROUP_CREATION = serializers.BooleanField(help_text='Allow users to create groups')
        FLOWBACK_ALLOW_DYNAMIC_POLL = serializers.BooleanField(help_text="Allow users to create dynamic polls")
        FLOWBACK_GROUP_ADMIN_USER_LIST_ACCESS_ONLY = serializers.BooleanField(
            help_text="Whether any group admins or superuser is able to list users or not or allow everyone to do that")
        FLOWBACK_DEFAULT_GROUP_JOIN = serializers.ListField(child=serializers.IntegerField(),
                                                            help_text="Default groups id's that users join")
        FLOWBACK_DISABLE_DEFAULT_USER_REGISTRATION = serializers.BooleanField(
            help_text="If users can register or not")
        GIT_HASH = serializers.CharField(help_text="The latest commit hash associated with this repository")

    def get(self, request):
        serializer = self.OutputSerializer(get_public_config())
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class ServerReportListAPI(APIView):
    class OutputSerializer(serializers.Serializer):
        title = serializers.CharField()
        description = serializers.CharField()
        group_id = serializers.IntegerField()
        post_id = serializers.IntegerField()
        post_type = serializers.CharField()

    def get(self, request):
        reports = reports_list(fetched_by=request.user)

        return get_paginated_response(pagination_class=LimitOffsetPagination,
                                      serializer_class=self.OutputSerializer,
                                      queryset=reports,
                                      request=request,
                                      view=self)
