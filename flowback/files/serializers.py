from rest_framework import serializers


class FileSerializer(serializers.Serializer):
    file = serializers.CharField()
    file_name = serializers.CharField()
