from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.user.models import Report
from flowback.user.services import report_create, report_update


@extend_schema(tags=['user'])
class ReportCreateAPI(APIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Report
            fields = ('title', 'description', 'group_id', 'post_id', 'post_type')

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report_create(user_id=request.user.id, **serializer.validated_data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['user'])
class ReportUpdateAPI(APIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Report
            fields = ('title', 'description', 'action_description', 'group_id', 'post_id', 'post_type')

    def post(self, request, report_id: int):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report_update(user_id=request.user.id, report_id=report_id, data=serializer.validated_data)
        
        return Response(serializer.data, status=status.HTTP_200_OK)