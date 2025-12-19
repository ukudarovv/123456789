from rest_framework import serializers

from .models import City, Category, TrainingFormat, TariffPlan


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name_ru", "name_kz")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "code", "name_ru", "name_kz")


class TrainingFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingFormat
        fields = ("id", "name_ru", "name_kz")


class TariffPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TariffPlan
        fields = ("id", "code", "name_ru", "name_kz")

