"""
Admin configuration for video encoding models.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models_encoding import MetadataExtractionSettings, VideoEncodingProfile


@admin.register(VideoEncodingProfile)
class VideoEncodingProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "resolution",
        "width",
        "height",
        "bitrate",
        "is_active",
        "order",
    )
    list_filter = ("is_active", "resolution")
    search_fields = ("name", "resolution")
    list_editable = ("is_active", "order")
    ordering = ("order", "name")

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("name", "resolution", "is_active", "order")},
        ),
        ("Параметры кодирования", {"fields": ("width", "height", "bitrate")}),
    )


@admin.register(MetadataExtractionSettings)
class MetadataExtractionSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "is_active",
        "poster_width",
        "poster_height",
        "preview_duration",
    )

    fieldsets = (
        (
            "Настройки постера",
            {
                "fields": (
                    "poster_width",
                    "poster_height",
                    "poster_format",
                    "poster_quality",
                )
            },
        ),
        (
            "Настройки превью",
            {
                "fields": (
                    "preview_width",
                    "preview_height",
                    "preview_duration",
                    "preview_segment_duration",
                    "preview_format",
                    "preview_quality",
                )
            },
        ),
        ("Общие настройки", {"fields": ("is_active",)}),
    )

    def has_add_permission(self, request):
        # Allow only one settings instance
        return not MetadataExtractionSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
