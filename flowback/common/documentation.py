from rest_framework import serializers
from drf_spectacular.openapi import AutoSchema


class CustomAutoSchema(AutoSchema):
    def get_override_parameters(self):
        view = self.view
        serializer_class = None

        get = getattr(view.__class__, 'get', None)

        if callable(get):
            if 'FilterSerializer' in dir(view.__class__):
                serializer_class = view.__class__.FilterSerializer

        if 'Pagination' in dir(view.__class__):
            pagination_class = view.__class__.Pagination

            class FilterSerializer(serializer_class if serializer_class is not None else serializers.Serializer):
                limit = serializers.IntegerField(default=pagination_class.default_limit,
                                                 max_value=pagination_class.max_limit)
                offset = serializers.IntegerField(required=False)

            serializer_class = FilterSerializer

        return [serializer_class] if serializer_class is not None else []

    def get_request_serializer(self):
        view = self.view

        post = getattr(view.__class__, 'post', None)

        if callable(post):
            if 'InputSerializer' in dir(view.__class__):
                return view.__class__.InputSerializer

    def get_response_serializers(self):
        view = self.view
        serializer_class = None

        if any(x in dir(view.__class__) for x in ['get', 'post']):
            if 'OutputSerializer' in dir(view.__class__):
                serializer_class = view.__class__.OutputSerializer

                if 'Pagination' in dir(view.__class__):
                    class OutputSerializer(serializer_class if serializer_class is not None
                                           else serializers.Serializer):
                        count = serializers.IntegerField()
                        next = serializers.URLField()
                        previous = serializers.URLField()
                        total_page = serializers.IntegerField()

                        if 'Meta' in dir(serializer_class):
                            class Meta(serializer_class.Meta):
                                fields = serializer_class.Meta.fields + ('count', 'next', 'previous', 'total_page')

                    OutputSerializer.__qualname__ = serializer_class.__qualname__
                    OutputSerializer.__module__ = serializer_class.__module__
                    OutputSerializer.__name__ = serializer_class.__name__
                    serializer_class = OutputSerializer

        return serializer_class

    def get_serializer_name(self, serializer, direction):
        prefix = ''.join([x.capitalize() for x in serializer.__class__.__module__.split('.')])
        prefix_2 = ''.join([x.replace('{', '').replace('}', '').capitalize() for x in self.path.split('/')[1:]])
        return f"{prefix_2}-{prefix}{serializer.__class__.__name__}{serializer.__class__.__qualname__.replace('.', '')}"

    def get_summary(self):
        return self.view.__class__.__name__.replace('API', '').replace('Api', '')
