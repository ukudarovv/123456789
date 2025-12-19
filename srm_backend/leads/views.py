import csv
import logging

from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import ApiKeyPermission
from .filters import LeadFilter
from .models import Lead, LeadStatusHistory
from .serializers import (
    LeadCreateSerializer,
    LeadShortSerializer,
    LeadDetailSerializer,
    LeadStatusUpdateSerializer,
)

logger = logging.getLogger(__name__)


class LeadCreateView(generics.CreateAPIView):
    serializer_class = LeadCreateSerializer
    permission_classes = [ApiKeyPermission]

    def create(self, request, *args, **kwargs):
        logger.info(f"Lead create request: {request.data}")
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Lead validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        lead = serializer.save()
        logger.info(f"Lead created: {lead.id}, type: {lead.type}")
        return Response({"id": str(lead.id), "status": lead.status}, status=status.HTTP_201_CREATED)


class LeadListView(generics.ListAPIView):
    serializer_class = LeadShortSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = LeadFilter
    queryset = Lead.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if hasattr(user, "role") and user.role == user.Roles.SCHOOL_MANAGER:
            qs = qs.filter(school=user.school)
        return qs.select_related("school", "city", "instructor")


class LeadDetailView(generics.RetrieveAPIView):
    serializer_class = LeadDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Lead.objects.all().prefetch_related("status_history")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if hasattr(user, "role") and user.role == user.Roles.SCHOOL_MANAGER:
            qs = qs.filter(school=user.school)
        return qs


class LeadStatusUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            lead = Lead.objects.get(pk=pk)
        except Lead.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        user = request.user
        if hasattr(user, "role") and user.role == user.Roles.SCHOOL_MANAGER and lead.school_id != user.school_id:
            return Response({"detail": "Forbidden"}, status=403)

        serializer = LeadStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_status = lead.status
        new_status = serializer.validated_data["status"]
        manager_comment = serializer.validated_data.get("manager_comment")
        lead.status = new_status
        lead.save(update_fields=["status"])
        LeadStatusHistory.objects.create(
            lead=lead, old_status=old_status, new_status=new_status, changed_by_user=user, note=manager_comment
        )
        return Response({"status": lead.status})


class LeadExportCsvView(generics.ListAPIView):
    serializer_class = LeadShortSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = LeadFilter
    queryset = Lead.objects.all()

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        user = request.user
        if hasattr(user, "role") and user.role == user.Roles.SCHOOL_MANAGER:
            qs = qs.filter(school=user.school)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=leads.csv"
        writer = csv.writer(response)
        writer.writerow(
            [
                "id",
                "type",
                "status",
                "name",
                "phone",
                "city_id",
                "category_id",
                "tariff_plan_id",
                "school_id",
                "instructor_id",
                "created_at",
            ]
        )
        for lead in qs:
            writer.writerow(
                [
                    lead.id,
                    lead.type,
                    lead.status,
                    lead.name,
                    lead.phone,
                    lead.city_id,
                    lead.category_id,
                    lead.tariff_plan_id,
                    lead.school_id,
                    lead.instructor_id,
                    lead.created_at.isoformat(),
                ]
            )
        return response

