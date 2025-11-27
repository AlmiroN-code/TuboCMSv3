from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.contrib import admin

from .models import Comment, CommentLike, CommentReport


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):    
    # WYSIWYG editor for comment content

    list_display = (
        "content_preview",
        "user",
        "video",
        "parent",
        "likes_count",
        "is_pinned",
        "created_at",
    )
    list_filter = ("is_pinned", "created_at", "updated_at")
    search_fields = ("content", "user__username", "video__title")
    readonly_fields = ("likes_count", "created_at", "updated_at")

    fieldsets = (
        ("Основная информация", {"fields": ("content", "user", "video", "parent")}),
        ("Модерация", {"fields": ("is_pinned",)}),
        ("Статистика", {"fields": ("likes_count",), "classes": ("collapse",)}),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def content_preview(self, obj):
        return (
            obj.content[:50] + "..."
            if obj.content and len(obj.content) > 50
            else obj.content
        )

    content_preview.short_description = "Content Preview"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "video", "parent")


@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ("comment", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("comment__content", "user__username")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("comment", "user")


@admin.register(CommentReport)
class CommentReportAdmin(admin.ModelAdmin):
    list_display = ("comment", "user", "report_type", "created_at", "is_resolved")
    list_filter = ("report_type", "is_resolved", "created_at")
    search_fields = ("comment__content", "user__username", "description")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("comment", "user")
