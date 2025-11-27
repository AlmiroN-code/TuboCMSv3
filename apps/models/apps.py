"""
Models app configuration.
"""
from django.apps import AppConfig


class ModelsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.models"
    verbose_name = "Models"

    def ready(self):
        import apps.models.signals
