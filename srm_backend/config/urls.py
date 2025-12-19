from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("leads.api_urls")),
    path("api/", include("dictionaries.api_urls")),
    path("api/", include("catalog.api_urls")),
    path("api/", include("analytics.api_urls")),
    path("api/", include("settings_app.api_urls")),
    path("srm/", include("srm_ui.urls")),
]

