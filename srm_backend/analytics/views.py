from rest_framework import generics

from accounts.permissions import ApiKeyPermission
from .models import AnalyticsEvent
from .serializers import AnalyticsEventSerializer


class AnalyticsEventCreateView(generics.CreateAPIView):
    serializer_class = AnalyticsEventSerializer
    permission_classes = [ApiKeyPermission]
    queryset = AnalyticsEvent.objects.all()

