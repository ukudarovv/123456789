from django.contrib import admin
from .models import City, Category, TrainingFormat, TariffPlan, TrainingTimeSlot, Gearbox


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "name_kz", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name_ru", "name_kz")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name_ru", "is_active", "show_in_tests", "sort_order")
    list_filter = ("is_active", "show_in_tests")
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


@admin.register(TrainingTimeSlot)
class TrainingTimeSlotAdmin(admin.ModelAdmin):
    list_display = ("code", "name_ru", "name_kz", "emoji", "time_range_ru", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name_ru", "name_kz")


@admin.register(Gearbox)
class GearboxAdmin(admin.ModelAdmin):
    list_display = ("code", "name_ru", "name_kz", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("code", "name_ru", "name_kz")

