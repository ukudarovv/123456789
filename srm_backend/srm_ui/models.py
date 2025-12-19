from django.db import models
from django.contrib.auth import get_user_model

from leads.models import Lead

User = get_user_model()


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        NEW_LEAD = "NEW_LEAD", "Новая заявка"
        STATUS_CHANGED = "STATUS_CHANGED", "Изменен статус"
        PAYMENT_ADDED = "PAYMENT_ADDED", "Добавлена ссылка на оплату"
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "srm_notification"
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
        ]
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.lead.id}"


class LeadComment(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "srm_lead_comment"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Comment on {self.lead.id} by {self.user.username}"
