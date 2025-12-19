from rest_framework import serializers

from .models import ProjectSetting, WhatsAppTemplate


class SettingsSerializer(serializers.Serializer):
    tests_price_kzt = serializers.IntegerField()
    owner_whatsapp = serializers.CharField()


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppTemplate
        fields = ("id", "scope", "language", "template_text", "is_active")

