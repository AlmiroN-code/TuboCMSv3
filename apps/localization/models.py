from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Rosetta(models.Model):
    """
    Model to represent Rosetta translation interface in admin.
    This is a proxy model for admin navigation - no database table.
    """

    class Meta:
        verbose_name = _("Rosetta")
        verbose_name_plural = _("Rosetta")
        app_label = "localization"
        managed = False  # No database table

    def __str__(self):
        return str(_("Rosetta Translation Interface"))

    @staticmethod
    def get_admin_url():
        """Return URL to Rosetta interface."""
        return "/rosetta/"


class LocalizationSettings(models.Model):
    """Localization settings for language and translation management."""

    rosetta_enabled = models.BooleanField(
        default=True,
        verbose_name=_("Включить Rosetta (интерфейс переводов)"),
        help_text=_("Включить управление переводами через /rosetta/"),
    )

    enable_user_language_preference = models.BooleanField(
        default=True,
        verbose_name=_("Разрешить пользователям выбирать язык"),
        help_text=_(
            "Показывать переключатель языка и сохранять предпочтения в профиле"
        ),
    )

    default_language = models.CharField(
        max_length=5,
        default="en",
        choices=[("en", "English"), ("ru", "Russian")],
        verbose_name=_("Язык по умолчанию"),
        help_text=_("Язык, используемый для гостей и новых пользователей"),
    )

    auto_detect_user_language = models.BooleanField(
        default=False,
        verbose_name=_("Автоматически определять язык браузера"),
        help_text=_("Устанавливать язык по Accept-Language заголовку браузера"),
    )

    enable_fuzzy_translations = models.BooleanField(
        default=True,
        verbose_name=_("Разрешить нечеткие переводы"),
        help_text=_("Показывать приблизительные переводы в Rosetta"),
    )

    translation_cache_timeout = models.PositiveIntegerField(
        default=3600,
        verbose_name=_("Время кэширования переводов (сек)"),
        help_text=_("Как долго кэшировать переведенные строки"),
    )

    # Активные настройки
    is_active = models.BooleanField(default=True, verbose_name=_("Активно"))

    class Meta:
        verbose_name = _("Настройки локализации")
        verbose_name_plural = _("Языки и локализация")
        app_label = "localization"

    def __str__(self):
        return str(_("Настройки локализации"))

    def save(self, *args, **kwargs):
        # Обеспечиваем, что только один экземпляр настроек активен
        if self.is_active:
            LocalizationSettings.objects.filter(is_active=True).exclude(
                pk=self.pk
            ).update(is_active=False)
        super().save(*args, **kwargs)
