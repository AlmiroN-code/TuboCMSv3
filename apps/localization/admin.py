from django.contrib import admin
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.contrib import admin

from .models import LocalizationSettings, Rosetta


@admin.register(Rosetta)
class RosettaAdmin(admin.ModelAdmin):
    """Admin interface for Rosetta translation tool."""

    # Hide model from changelist, redirect directly to Rosetta
    def changelist_view(self, request, extra_context=None):
        """Redirect to Rosetta interface instead of showing changelist."""
        return redirect("/rosetta/")

    def has_add_permission(self, request):
        """Disable adding new Rosetta objects."""
        return False

    def has_change_permission(self, request, obj=None):
        """Allow viewing (which redirects to Rosetta)."""
        return True

    def has_delete_permission(self, request, obj=None):
        """Disable deleting Rosetta objects."""
        return False

    # Customize the changelist display
    list_display = []
    list_display_links = None
    search_fields = []
    list_filter = []

    def get_queryset(self, request):
        """Return empty queryset since there's no database model."""
        return self.model.objects.none()

    # Custom changeform template to redirect
    change_form_template = None
    change_list_template = "admin/localization/rosetta_changelist.html"

    # Disable breadcrumbs for this view
    def get_model_perms(self, request):
        """Return permissions for the model."""
        return {
            "add": False,
            "change": True,
            "delete": False,
            "view": True,
        }


@admin.register(LocalizationSettings)
class LocalizationSettingsAdmin(admin.ModelAdmin):
    list_display = ["default_language", "is_active"]

    fieldsets = (
        (
            _("Основные настройки локализации"),
            {
                "fields": (
                    "rosetta_enabled",
                    "enable_user_language_preference",
                    "default_language",
                )
            },
        ),
        (
            _("Расширенные настройки"),
            {
                "fields": (
                    "auto_detect_user_language",
                    "enable_fuzzy_translations",
                    "translation_cache_timeout",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Системные настройки", {"fields": ("is_active",), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        # Разрешаем добавлять только если нет активных настроек
        return not LocalizationSettings.objects.filter(is_active=True).exists()

    def has_delete_permission(self, request, obj=None):
        # Не разрешаем удалять активные настройки
        if obj and obj.is_active:
            return False
        return True
