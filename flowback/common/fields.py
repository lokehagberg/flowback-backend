from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.utils import html


class CharacterSeparatedField(serializers.ListField):
    def __init__(self, **kwargs):
        self.separator = kwargs.pop("separator", ",")
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = data.split(self.separator)
        elif not isinstance(data, list):
            raise serializers.ValidationError(f"Invalid input type, "
                                              f"field expects a string separated by: {self.separator}")
        return super().to_internal_value(data)

    def get_value(self, dictionary):
        # We override the default field access in order to support
        # lists in HTML forms.
        if html.is_html_input(dictionary):
            # Don't return [] if the update is partial
            if self.field_name not in dictionary:
                if getattr(self.root, "partial", False):
                    return empty
            return dictionary.get(self.field_name)

        return dictionary.get(self.field_name, empty)

    def to_representation(self, data):
        data = super().to_representation(data)
        return self.separator.join(data)