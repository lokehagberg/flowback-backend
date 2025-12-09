from rest_framework import serializers


class FileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    file = serializers.CharField()
    file_name = serializers.CharField()


class FileCollectionListSerializerMixin:
    attachments = FileSerializer(many=True, source='attachments.filesegment_set', allow_null=True)


class FileCollectionCreateSerializerMixin:
    attachments = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)


class FileCollectionUpdateSerializerMixin:
    attachments_add = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)
    attachments_remove = serializers.ListField(child=serializers.IntegerField(), required=False)
