"""
Admin configuration for models app.
"""
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import admin

from .forms import ModelForm
from .models import Model, ModelLike, ModelSubscription, ModelVideo


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    form = ModelForm    # WYSIWYG editor for bio field

    list_display = (
        "display_name",
        "user",
        "gender",
        "age",
        "country",
        "is_verified",
        "is_active",
        "views_count",
        "subscribers_count",
        "videos_count",
        "created_at",
    )
    list_filter = (
        "gender",
        "is_verified",
        "is_active",
        "is_premium",
        "hair_color",
        "eye_color",
        "country",
        "created_at",
    )
    search_fields = (
        "display_name",
        "user__username",
        "user__email",
        "bio",
        "country",
        "ethnicity",
    )
    readonly_fields = (
        "views_count",
        "subscribers_count",
        "videos_count",
        "likes_count",
        "created_at",
        "updated_at",
        "avatar_display",
        "cover_photo_display",
    )
    filter_horizontal = ()

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "user",
                    "display_name",
                    "slug",
                    "bio",
                    "avatar",
                    "cover_photo",
                )
            },
        ),
        (
            "Личная информация",
            {
                "fields": (
                    "gender",
                    "age",
                    "birth_date",
                    "country",
                    "ethnicity",
                    "career_start",
                    "zodiac_sign",
                )
            },
        ),
        (
            "Физические характеристики",
            {
                "fields": (
                    "hair_color",
                    "eye_color",
                    "has_tattoos",
                    "tattoos_description",
                    "has_piercings",
                    "piercings_description",
                )
            },
        ),
        ("Размеры", {"fields": ("breast_size", "measurements", "height", "weight")}),
        ("Статус", {"fields": ("is_verified", "is_active", "is_premium")}),
        (
            "Статистика",
            {
                "fields": (
                    "views_count",
                    "subscribers_count",
                    "videos_count",
                    "likes_count",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def avatar_display(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" width="100" height="100" style="border-radius: 50%; object-fit: cover;" />',
                obj.avatar.url,
            )
        return "No Avatar"

    avatar_display.short_description = "Avatar"

    def cover_photo_display(self, obj):
        if obj.cover_photo:
            return format_html(
                '<img src="{}" width="200" height="100" style="object-fit: cover;" />',
                obj.cover_photo.url,
            )
        return "No Cover Photo"

    cover_photo_display.short_description = "Cover Photo"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


@admin.register(ModelVideo)
class ModelVideoAdmin(admin.ModelAdmin):
    list_display = ("model", "video", "is_primary", "created_at")
    list_filter = ("is_primary", "created_at")
    search_fields = ("model__display_name", "video__title")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("model", "video")


@admin.register(ModelSubscription)
class ModelSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "model", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "model__display_name")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "model")


@admin.register(ModelLike)
class ModelLikeAdmin(admin.ModelAdmin):
    list_display = ("user", "model", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "model__display_name")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "model")
