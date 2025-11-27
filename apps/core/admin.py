from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.contrib import admin

from .models import Category, SEOSettings, SiteSettings, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):    
    # WYSIWYG editor for description field


    list_display = (
        "name",
        "slug",
        "description_preview",
        "is_active",
        "order",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}

    def description_preview(self, obj):
        return (
            obj.description[:50] + "..."
            if obj.description and len(obj.description) > 50
            else obj.description
        )

    description_preview.short_description = "Description Preview"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ["site_name", "is_active", "created_at"]
    list_filter = [
        "is_active",
        "allow_registration",
        "auto_publish_videos",
        "require_moderation",
    ]

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "site_name",
                    "site_logo",
                    "site_favicon",
                    "add_site_name_to_title",
                )
            },
        ),
        (
            "Контактная информация",
            {
                "fields": ("contact_email", "contact_phone", "contact_address"),
                "classes": ("collapse",),
            },
        ),
        (
            "Социальные сети",
            {
                "fields": (
                    "social_vk",
                    "social_telegram",
                    "social_youtube",
                    "social_twitter",
                    "social_instagram",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Настройки видео",
            {
                "fields": (
                    "max_video_size",
                    "max_video_duration",
                    "allowed_video_formats",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Настройки пользователей",
            {
                "fields": (
                    "allow_registration",
                    "require_email_verification",
                    "max_upload_per_day",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Настройки модерации",
            {
                "fields": ("auto_publish_videos", "require_moderation"),
                "classes": ("collapse",),
            },
        ),
        (
            "Системные настройки",
            {"fields": ("cache_timeout", "is_active"), "classes": ("collapse",)},
        ),
    )

    def has_add_permission(self, request):
        # Разрешаем добавлять только если нет активных настроек
        return not SiteSettings.objects.filter(is_active=True).exists()

    def has_delete_permission(self, request, obj=None):
        # Не разрешаем удалять активные настройки
        if obj and obj.is_active:
            return False
        return True


@admin.register(SEOSettings)
class SEOSettingsAdmin(admin.ModelAdmin):
    list_display = ["meta_title", "is_active", "created_at"]
    list_filter = ["is_active", "sitemap_enabled"]

    fieldsets = (
        ("Meta теги", {"fields": ("meta_title", "meta_description", "meta_keywords")}),
        (
            "Open Graph",
            {
                "fields": ("og_title", "og_description", "og_image"),
                "classes": ("collapse",),
            },
        ),
        (
            "Twitter Card",
            {
                "fields": ("twitter_card", "twitter_site", "twitter_creator"),
                "classes": ("collapse",),
            },
        ),
        (
            "Google Analytics",
            {
                "fields": ("google_analytics_id", "google_tag_manager_id"),
                "classes": ("collapse",),
            },
        ),
        (
            "Яндекс.Метрика",
            {"fields": ("yandex_metrica_id",), "classes": ("collapse",)},
        ),
        (
            "Другие счетчики",
            {"fields": ("facebook_pixel_id", "vk_pixel_id"), "classes": ("collapse",)},
        ),
        (
            "Структурированные данные",
            {
                "fields": (
                    "organization_name",
                    "organization_logo",
                    "organization_description",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Настройки индексации",
            {"fields": ("robots_txt", "sitemap_enabled"), "classes": ("collapse",)},
        ),
        ("Системные настройки", {"fields": ("is_active",), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        # Разрешаем добавлять только если нет активных SEO настроек
        return not SEOSettings.objects.filter(is_active=True).exists()

    def has_delete_permission(self, request, obj=None):
        # Не разрешаем удалять активные SEO настройки
        if obj and obj.is_active:
            return False
        return True
