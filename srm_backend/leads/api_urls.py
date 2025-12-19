from django.urls import path

from .views import (
    LeadCreateView,
    LeadListView,
    LeadDetailView,
    LeadStatusUpdateView,
    LeadExportCsvView,
)

urlpatterns = [
    path("leads", LeadCreateView.as_view()),  # POST for bot
    path("leads/list", LeadListView.as_view()),  # GET for SRM
    path("leads/<uuid:pk>", LeadDetailView.as_view()),  # GET detail
    path("leads/<uuid:pk>/status", LeadStatusUpdateView.as_view()),  # PATCH status
    path("leads/export", LeadExportCsvView.as_view()),  # GET CSV
]

