from django.apps import AppConfig


class SrmUiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'srm_ui'
    
    def ready(self):
        import srm_ui.signals  # noqa