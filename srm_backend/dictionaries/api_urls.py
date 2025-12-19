from django.urls import path

from .views import (
    CityListView,
    CategoryListView,
    TrainingFormatListView,
    TariffPlanListView,
)

urlpatterns = [
    path("dicts/cities", CityListView.as_view()),
    path("dicts/categories", CategoryListView.as_view()),
    path("dicts/training-formats", TrainingFormatListView.as_view()),
    path("dicts/tariff-plans", TariffPlanListView.as_view()),
]

