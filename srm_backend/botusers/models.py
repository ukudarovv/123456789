from django.db import models


class BotUser(models.Model):
    LANGUAGE_CHOICES = (
        ("RU", "Russian"),
        ("KZ", "Kazakh"),
    )

    telegram_user_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES)
    phone = models.CharField(max_length=32, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "bot_user"
        ordering = ["id"]

    def __str__(self):
        return f"{self.telegram_user_id}"

