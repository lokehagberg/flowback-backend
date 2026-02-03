from rest_framework import serializers


class FileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    file = serializers.CharField()
    file_name = serializers.CharField()


class FileCollectionListSerializerMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, 'attachments'):
            self.fields['attachments'] = FileSerializer(many=True, source='attachments.filesegment_set', allow_null=True)


class FileCollectionCreateSerializerMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, 'attachments'):
            self.fields['attachments'] = serializers.ListField(child=serializers.FileField(), required=False, max_length=10)


class FileCollectionUpdateSerializerMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, 'attachments_add'):
            self.fields['attachments_add'] = serializers.ListField(child=serializers.FileField(), required=False,
                                                                   max_length=10)
        if not hasattr(self, 'attachments_remove'):
            self.fields['attachments_remove'] = serializers.ListField(child=serializers.IntegerField(), required=False)