import django_filters


class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    pass


class ExistsFilter(django_filters.BooleanFilter):
    def __init__(self, *args, **kwargs):
        kwargs['method'] = self.has_attachments_filter
        super().__init__(*args, **kwargs)

    @staticmethod
    def has_attachments_filter(queryset, name, value):
        data = {f"{name}__isnull": not value}
        return queryset.filter(**data)
