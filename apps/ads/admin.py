"""
Admin configuration for ads app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import admin

from .models import AdBanner, AdCampaign, AdClick, AdImpression, AdPlacement, AdZone


@admin.register(AdPlacement)
class AdPlacementAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "placement_type",
        "width",
        "height",
        "is_active",
        "created_at",
    )
    list_filter = ("placement_type", "is_active", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("name", "slug", "placement_type", "description")},
        ),
        ("Размеры", {"fields": ("width", "height")}),
        ("Настройки", {"fields": ("is_active",)}),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "advertiser",
        "status",
        "budget",
        "start_date",
        "end_date",
        "is_active",
        "created_at",
    )
    list_filter = ("status", "is_active", "start_date", "end_date", "created_at")
    search_fields = ("name", "description", "advertiser__username")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Основная информация", {"fields": ("name", "advertiser", "description")}),
        ("Бюджет и даты", {"fields": ("budget", "start_date", "end_date")}),
        (
            "Цели",
            {
                "fields": ("target_impressions", "target_clicks"),
                "classes": ("collapse",),
            },
        ),
        ("Настройки", {"fields": ("status", "is_active")}),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(AdBanner)
class AdBannerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "campaign",
        "placement",
        "banner_type",
        "is_active",
        "priority",
        "impressions_count",
        "clicks_count",
        "ctr_display",
        "created_at",
    )
    list_filter = ("banner_type", "is_active", "campaign", "placement", "created_at")
    search_fields = ("name", "alt_text", "target_url")
    readonly_fields = (
        "impressions_count",
        "clicks_count",
        "ctr_display",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("name", "campaign", "placement", "banner_type")},
        ),
        (
            "Контент",
            {"fields": ("image", "video", "html_content", "text_content", "alt_text")},
        ),
        ("Ссылка", {"fields": ("target_url",)}),
        ("Настройки отображения", {"fields": ("is_active", "priority", "weight")}),
        (
            "Статистика",
            {
                "fields": ("impressions_count", "clicks_count", "ctr_display"),
                "classes": ("collapse",),
            },
        ),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def ctr_display(self, obj):
        """Display CTR as percentage."""
        return f"{obj.ctr:.2f}%"

    ctr_display.short_description = "CTR"
    ctr_display.admin_order_field = "ctr"


@admin.register(AdImpression)
class AdImpressionAdmin(admin.ModelAdmin):
    list_display = ("banner", "ip_address", "created_at")
    list_filter = ("banner__campaign", "banner__placement", "created_at")
    search_fields = ("banner__name", "ip_address")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("banner", "banner__campaign", "banner__placement")
        )


@admin.register(AdClick)
class AdClickAdmin(admin.ModelAdmin):
    list_display = ("banner", "ip_address", "created_at")
    list_filter = ("banner__campaign", "banner__placement", "created_at")
    search_fields = ("banner__name", "ip_address")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("banner", "banner__campaign", "banner__placement")
        )


@admin.register(AdZone)
class AdZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "placements_count", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("placements",)

    fieldsets = (
        ("Основная информация", {"fields": ("name", "slug", "description")}),
        ("Места размещения", {"fields": ("placements",)}),
        ("Настройки", {"fields": ("is_active",)}),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def placements_count(self, obj):
        """Display number of placements in zone."""
        return obj.placements.count()

    placements_count.short_description = "Количество мест"
