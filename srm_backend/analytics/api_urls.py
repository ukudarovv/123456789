from django.urls import path

from .views import AnalyticsEventCreateView

urlpatterns = [
    path("analytics/events", AnalyticsEventCreateView.as_view()),
]

