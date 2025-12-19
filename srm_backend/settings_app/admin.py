from django.contrib import admin

from .models import ProjectSetting, WhatsAppTemplate


@admin.register(ProjectSetting)
class ProjectSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "updated_at")
    search_fields = ("key",)


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = ("scope", "language", "is_active")
    list_filter = ("scope", "language", "is_active")
    search_fields = ("scope",)

