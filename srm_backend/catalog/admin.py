from django.contrib import admin

from .models import School, SchoolTariff, Instructor, InstructorTariff


class SchoolTariffInline(admin.StackedInline):
    model = SchoolTariff
    extra = 1
    filter_horizontal = ("categories", "training_times", "gearboxes",)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name_ru", "city", "rating", "trust_index", "is_active")
    list_filter = ("city", "is_active")
    search_fields = ("name_ru", "name_kz", "address_ru", "address_kz")
    inlines = [SchoolTariffInline]


@admin.register(SchoolTariff)
class SchoolTariffAdmin(admin.ModelAdmin):
    list_display = ("school", "tariff_name", "training_format", "price_kzt", "is_active")
    list_filter = ("training_format", "is_active", "gearboxes")
    search_fields = ("school__name_ru", "tariff_name")
    filter_horizontal = ("categories", "training_times", "gearboxes",)


class InstructorTariffInline(admin.TabularInline):
    model = InstructorTariff
    extra = 1


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ("display_name", "city", "gearbox", "gender", "is_active")
    list_filter = ("city", "gearbox", "gender", "is_active")
    search_fields = ("display_name",)
    filter_horizontal = ("categories",)
    inlines = [InstructorTariffInline]


@admin.register(InstructorTariff)
class InstructorTariffAdmin(admin.ModelAdmin):
    list_display = ("instructor", "tariff_type", "price_kzt", "is_active")
    list_filter = ("tariff_type", "is_active")
    search_fields = ("instructor__display_name",)

