from rest_framework import generics

from accounts.permissions import ApiKeyPermission
from .models import City, Category, TrainingFormat, TariffPlan, TrainingTimeSlot
from .serializers import (
    CitySerializer,
    CategorySerializer,
    TrainingFormatSerializer,
    TariffPlanSerializer,
    TrainingTimeSlotSerializer,
)


class CityListView(generics.ListAPIView):
    serializer_class = CitySerializer
    permission_classes = [ApiKeyPermission]

    def get_queryset(self):
        qs = City.objects.all()
        if self.request.query_params.get("is_active", "true").lower() == "true":
            qs = qs.filter(is_active=True)
        return qs


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [ApiKeyPermission]

    def get_queryset(self):
        qs = Category.objects.all()
        if self.request.query_params.get("is_active", "true").lower() == "true":
            qs = qs.filter(is_active=True)
        return qs


class TrainingFormatListView(generics.ListAPIView):
    serializer_class = TrainingFormatSerializer
    permission_classes = [ApiKeyPermission]

    def get_queryset(self):
        qs = TrainingFormat.objects.all()
        if self.request.query_params.get("is_active", "true").lower() == "true":
            qs = qs.filter(is_active=True)
        return qs


class TariffPlanListView(generics.ListAPIView):
    serializer_class = TariffPlanSerializer
    permission_classes = [ApiKeyPermission]

    def get_queryset(self):
        qs = TariffPlan.objects.all()
        if self.request.query_params.get("is_active", "true").lower() == "true":
            qs = qs.filter(is_active=True)
        return qs


class TrainingTimeSlotListView(generics.ListAPIView):
    serializer_class = TrainingTimeSlotSerializer
    permission_classes = [ApiKeyPermission]

    def get_queryset(self):
        qs = TrainingTimeSlot.objects.all()
        if self.request.query_params.get("is_active", "true").lower() == "true":
            qs = qs.filter(is_active=True)
        return qs

