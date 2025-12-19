from django.contrib import admin

from .models import Lead, LeadStatusHistory


class LeadStatusHistoryInline(admin.TabularInline):
    model = LeadStatusHistory
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by_user", "changed_at", "note")
    can_delete = False


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "status", "name", "phone", "city", "school", "instructor", "created_at")
    list_filter = ("type", "status", "city", "school")
    search_fields = ("id", "name", "phone")
    inlines = [LeadStatusHistoryInline]


@admin.register(LeadStatusHistory)
class LeadStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("lead", "old_status", "new_status", "changed_by_user", "changed_at")
    list_filter = ("new_status",)
    search_fields = ("lead__id",)

