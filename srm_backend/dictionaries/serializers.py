from rest_framework import serializers

from .models import City, Category, TrainingFormat, TariffPlan, TrainingTimeSlot


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ("id", "name_ru", "name_kz")
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Удаляем null/None значения
        return {k: v for k, v in data.items() if v is not None}


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "code", "name_ru", "name_kz")
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Удаляем null/None значения и code
        return {k: v for k, v in data.items() if v is not None and k != "code"}


class TrainingFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingFormat
        fields = ("id", "name_ru", "name_kz")
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Удаляем null/None значения
        return {k: v for k, v in data.items() if v is not None}


class TariffPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TariffPlan
        fields = ("id", "code", "name_ru", "name_kz")
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Удаляем null/None значения и code
        return {k: v for k, v in data.items() if v is not None and k != "code"}


class TrainingTimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingTimeSlot
        fields = ("id", "code", "name_ru", "name_kz", "emoji", "time_range_ru", "time_range_kz")
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Удаляем null/None значения и code
        return {k: v for k, v in data.items() if v is not None and k != "code"}

