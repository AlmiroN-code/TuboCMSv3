from django.apps import AppConfig


class AdminSettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.admin_settings'
    verbose_name = 'Настройки'