"""
Apps configuration for ads app.
"""
from django.apps import AppConfig


class AdsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ads"
    verbose_name = "Реклама"
