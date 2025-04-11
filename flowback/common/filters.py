import django_filters


# Basic filter for list of numbers
class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass

class StringInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass

# Check whether attachments exist or not
# TODO check if relevant
class ExistsFilter(django_filters.BooleanFilter):
    def __init__(self, *args, **kwargs):
        kwargs['method'] = self.has_attachments_filter
        super().__init__(*args, **kwargs)

    @staticmethod
    def has_attachments_filter(queryset, name, value):
        data = {f"{name}__isnull": not value}
        return queryset.filter(**data)
