from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LocalizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.localization"
    verbose_name = _("Localization")
