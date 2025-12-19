from django.db import models

from botusers.models import BotUser
from leads.models import Lead


class AnalyticsEvent(models.Model):
    bot_user = models.ForeignKey(BotUser, on_delete=models.SET_NULL, null=True, blank=True)
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True)
    event_name = models.CharField(max_length=50)
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "analytics_event"
        indexes = [
            models.Index(fields=["event_name", "created_at"]),
            models.Index(fields=["bot_user", "created_at"]),
            models.Index(fields=["lead", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.event_name

