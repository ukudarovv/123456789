from django.urls import path
from . import views

app_name = "srm_ui"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("leads/", views.lead_list, name="lead_list"),
    path("leads/bulk-action/", views.bulk_action, name="bulk_action"),
    path("leads/<uuid:lead_id>/", views.lead_detail, name="lead_detail"),
    path("leads/<uuid:lead_id>/status/", views.lead_status_update, name="lead_status_update"),
    path("leads/<uuid:lead_id>/whatsapp/", views.lead_whatsapp_link, name="lead_whatsapp_link"),
    path("leads/<uuid:lead_id>/payment-link/", views.lead_payment_link_update, name="lead_payment_link_update"),
    path("leads/<uuid:lead_id>/comments/", views.get_comments, name="get_comments"),
    path("leads/<uuid:lead_id>/comments/add/", views.add_comment, name="add_comment"),
    path("notifications/", views.notification_list, name="notification_list"),
    path("notifications/count/", views.notification_count, name="notification_count"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("analytics/", views.analytics, name="analytics"),
    path("whatsapp-templates/", views.whatsapp_template_list, name="whatsapp_template_list"),
    path("whatsapp-templates/<int:template_id>/edit/", views.whatsapp_template_edit, name="whatsapp_template_edit"),
    path("whatsapp-templates/new/", views.whatsapp_template_edit, name="whatsapp_template_new"),
]

