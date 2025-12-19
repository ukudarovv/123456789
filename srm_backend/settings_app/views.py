import os
from rest_framework import generics
from rest_framework.response import Response

from accounts.permissions import ApiKeyPermission
from .models import ProjectSetting, WhatsAppTemplate
from .serializers import SettingsSerializer, WhatsAppTemplateSerializer


def get_setting_value(key, default=None):
    try:
        obj = ProjectSetting.objects.get(key=key)
        return obj.value_json
    except ProjectSetting.DoesNotExist:
        return os.getenv(key, default)


class SettingsView(generics.GenericAPIView):
    permission_classes = [ApiKeyPermission]

    def get(self, request, *args, **kwargs):
        data = {
            "tests_price_kzt": int(get_setting_value("TESTS_PRICE_KZT", 0)),
            "owner_whatsapp": get_setting_value("OWNER_WHATSAPP_PHONE", ""),
        }
        serializer = SettingsSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class WhatsAppTemplateListView(generics.ListAPIView):
    serializer_class = WhatsAppTemplateSerializer
    permission_classes = [ApiKeyPermission]

    def get_queryset(self):
        qs = WhatsAppTemplate.objects.filter(is_active=True)
        scope = self.request.query_params.get("scope")
        language = self.request.query_params.get("language")
        if scope:
            qs = qs.filter(scope=scope)
        if language:
            qs = qs.filter(language=language)
        return qs

