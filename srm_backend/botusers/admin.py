from django.contrib import admin
from .models import BotUser


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ("telegram_user_id", "username", "language", "phone", "created_at")
    search_fields = ("telegram_user_id", "username", "phone")

