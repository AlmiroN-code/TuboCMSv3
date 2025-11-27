"""
Videos app configuration.
"""
from django.apps import AppConfig


class VideosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.videos"
    verbose_name = "Videos"

    def ready(self):
        """Import admin and signals when app is ready."""
        import apps.videos.admin
        import apps.videos.admin_encoding
        import apps.videos.signals
