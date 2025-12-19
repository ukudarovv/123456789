from django.contrib import admin
from .models import City, Category, TrainingFormat, TariffPlan


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_kz", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name_ru", "name_kz")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name_ru", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name_ru", "name_kz")


@admin.register(TrainingFormat)
class TrainingFormatAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_kz", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name_ru", "name_kz")


@admin.register(TariffPlan)
class TariffPlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name_ru", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name_ru", "name_kz")

