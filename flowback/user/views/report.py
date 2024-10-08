from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from flowback.user.models import Report
from flowback.user.services import report_create


class ReportCreateAPI(APIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Report
            fields = ('title', 'description',)

    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        report_create(user_id=request.user.id, **serializer.validated_data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
