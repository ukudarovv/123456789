from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import SrmUser


@admin.register(SrmUser)
class SrmUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("SRM Role", {"fields": ("role", "school")}),
    )
    list_display = ("username", "email", "role", "school", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")

