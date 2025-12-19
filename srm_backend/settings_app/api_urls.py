from django.urls import path

from .views import SettingsView, WhatsAppTemplateListView

urlpatterns = [
    path("settings", SettingsView.as_view()),
    path("settings/whatsapp-templates", WhatsAppTemplateListView.as_view()),
]

