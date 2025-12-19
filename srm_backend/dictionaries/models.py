from django.db import models


class City(models.Model):
    name_ru = models.CharField(max_length=255)
    name_kz = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "dict_city"
        indexes = [
            models.Index(fields=["is_active", "sort_order"]),
        ]
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name_ru


class Category(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name_ru = models.CharField(max_length=255)
    name_kz = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "dict_category"
        indexes = [
            models.Index(fields=["is_active", "sort_order"]),
        ]
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.code


class TrainingFormat(models.Model):
    name_ru = models.CharField(max_length=255)
    name_kz = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "dict_training_format"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name_ru


class TariffPlan(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name_ru = models.CharField(max_length=255)
    name_kz = models.CharField(max_length=255)
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "dict_tariff_plan"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.code

