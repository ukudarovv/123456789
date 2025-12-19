from rest_framework import serializers

from .models import AnalyticsEvent


class AnalyticsEventSerializer(serializers.ModelSerializer):
    bot_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    lead_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = AnalyticsEvent
        fields = ("id", "bot_user", "lead", "bot_user_id", "lead_id", "event_name", "payload", "created_at")
        read_only_fields = ("id", "bot_user", "lead", "created_at")
        extra_kwargs = {
            "event_name": {"required": True},
        }

    def create(self, validated_data):
        bot_user_id = validated_data.pop("bot_user_id", None)
        lead_id = validated_data.pop("lead_id", None)
        
        if bot_user_id:
            from botusers.models import BotUser
            try:
                validated_data["bot_user"] = BotUser.objects.get(id=bot_user_id)
            except BotUser.DoesNotExist:
                validated_data["bot_user"] = None
        
        if lead_id:
            from leads.models import Lead
            try:
                validated_data["lead"] = Lead.objects.get(id=lead_id)
            except Lead.DoesNotExist:
                validated_data["lead"] = None
        
        return super().create(validated_data)

