import django_filters

from .models import Lead


class LeadFilter(django_filters.FilterSet):
    created_from = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_to = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Lead
        fields = ["status", "type", "city", "school", "phone"]

