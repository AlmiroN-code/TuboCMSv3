"""
Core models for TubeCMS.
"""

import time

from django.db import models

from .managers import (
    CategoryManager,
    SEOSettingsManager,
    SiteSettingsManager,
    TagManager,
)


class TimeStampedModel(models.Model):
    """Abstract base class with self-updating 'created' and 'modified' fields."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    """Video categories."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=50, blank=True, help_text="Font Awesome icon class"
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    # Managers
    objects = CategoryManager()

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generate slug from name if empty
        if not self.slug and self.name:
            from django.utils.text import slugify

            try:
                import transliterate

                name_latin = transliterate.translit(self.name, "ru", reversed=True)
                base_slug = slugify(name_latin)
            except Exception:
                base_slug = slugify(self.name)

            self.slug = base_slug or "category"
        super().save(*args, **kwargs)
        # Инвалидируем кэш категорий
        from django.core.cache import cache

        cache.delete("categories_active")


class Tag(TimeStampedModel):
    """Video tags."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    color = models.CharField(
        max_length=7, default="#ff0000", help_text="Hex color code"
    )

    # Managers
    objects = TagManager()

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug from name if empty."""
        if not self.slug and self.name:
            from django.utils.text import slugify

            try:
                import transliterate

                name_latin = transliterate.translit(self.name, "ru", reversed=True)
                base_slug = slugify(name_latin)
            except Exception:
                base_slug = slugify(self.name)

            self.slug = base_slug or "tag"
            # Ensure uniqueness
            counter = 1
            while Tag.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)


class SiteSettings(TimeStampedModel):
    """Основные настройки сайта."""

    site_name = models.CharField(
        max_length=100, default="TubeCMS", verbose_name="Название сайта"
    )
    site_logo = models.ImageField(
        upload_to="settings/", blank=True, null=True, verbose_name="Логотип сайта"
    )
    site_favicon = models.ImageField(
        upload_to="settings/", blank=True, null=True, verbose_name="Фавикон"
    )
    add_site_name_to_title = models.BooleanField(
        default=True, verbose_name="Добавлять в тег title страницы название сайта"
    )

    # Контактная информация
    contact_email = models.EmailField(blank=True, verbose_name="Контактный email")
    contact_phone = models.CharField(
        max_length=20, blank=True, verbose_name="Контактный телефон"
    )
    contact_address = models.TextField(blank=True, verbose_name="Адрес")

    # Социальные сети
    social_vk = models.URLField(blank=True, verbose_name="VK")
    social_telegram = models.URLField(blank=True, verbose_name="Telegram")
    social_youtube = models.URLField(blank=True, verbose_name="YouTube")
    social_twitter = models.URLField(blank=True, verbose_name="Twitter")
    social_instagram = models.URLField(blank=True, verbose_name="Instagram")

    # Настройки видео
    max_video_size = models.PositiveIntegerField(
        default=500, verbose_name="Максимальный размер видео (MB)"
    )
    max_video_duration = models.PositiveIntegerField(
        default=3600, verbose_name="Максимальная длительность видео (сек)"
    )
    allowed_video_formats = models.CharField(
        max_length=200,
        default="mp4,avi,mov,wmv",
        verbose_name="Разрешенные форматы видео",
    )

    # Настройки пользователей
    allow_registration = models.BooleanField(
        default=True, verbose_name="Разрешить регистрацию"
    )
    require_email_verification = models.BooleanField(
        default=False, verbose_name="Требовать подтверждение email"
    )
    max_upload_per_day = models.PositiveIntegerField(
        default=10, verbose_name="Максимум загрузок в день на пользователя"
    )

    # Настройки модерации
    auto_publish_videos = models.BooleanField(
        default=False, verbose_name="Автоматически публиковать видео"
    )
    require_moderation = models.BooleanField(
        default=True, verbose_name="Требовать модерацию"
    )

    # Настройки кэширования
    cache_timeout = models.PositiveIntegerField(
        default=300, verbose_name="Время кэширования (сек)"
    )

    # Активные настройки
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "Основные настройки"
        verbose_name_plural = "Основные настройки"

    def __str__(self):
        return f"Настройки сайта - {self.site_name}"

    def save(self, *args, **kwargs):
        # Обеспечиваем, что только один экземпляр настроек активен
        if self.is_active:
            max_retries = 3
            retry_delay = 0.1

            for attempt in range(max_retries):
                try:
                    # Исключаем текущий объект из обновления, если он уже существует
                    queryset = SiteSettings.objects.filter(is_active=True)
                    if self.pk:
                        queryset = queryset.exclude(pk=self.pk)
                    queryset.update(is_active=False)
                    break
                except Exception:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    # Если все попытки неудачны, продолжаем сохранение
                    pass

        super().save(*args, **kwargs)
        # Инвалидируем кэш настроек сайта
        from django.core.cache import cache

        cache.delete("site_settings_active")


class SEOSettings(TimeStampedModel):
    """SEO и аналитические настройки."""

    # Meta теги
    meta_title = models.CharField(max_length=60, blank=True, verbose_name="Meta Title")
    meta_description = models.TextField(blank=True, verbose_name="Meta Description")
    meta_keywords = models.CharField(
        max_length=500, blank=True, verbose_name="Meta Keywords"
    )

    # Open Graph
    og_title = models.CharField(max_length=60, blank=True, verbose_name="OG Title")
    og_description = models.CharField(
        max_length=160, blank=True, verbose_name="OG Description"
    )
    og_image = models.ImageField(
        upload_to="settings/", blank=True, null=True, verbose_name="OG Image"
    )

    # Twitter Card
    twitter_card = models.CharField(
        max_length=20, default="summary_large_image", verbose_name="Twitter Card Type"
    )
    twitter_site = models.CharField(
        max_length=50, blank=True, verbose_name="Twitter Site"
    )
    twitter_creator = models.CharField(
        max_length=50, blank=True, verbose_name="Twitter Creator"
    )

    # Google Analytics
    google_analytics_id = models.CharField(
        max_length=20, blank=True, verbose_name="Google Analytics ID"
    )
    google_tag_manager_id = models.CharField(
        max_length=20, blank=True, verbose_name="Google Tag Manager ID"
    )

    # Яндекс.Метрика
    yandex_metrica_id = models.CharField(
        max_length=20, blank=True, verbose_name="Яндекс.Метрика ID"
    )

    # Другие счетчики
    facebook_pixel_id = models.CharField(
        max_length=20, blank=True, verbose_name="Facebook Pixel ID"
    )
    vk_pixel_id = models.CharField(
        max_length=20, blank=True, verbose_name="VK Pixel ID"
    )

    # Структурированные данные
    organization_name = models.CharField(
        max_length=100, blank=True, verbose_name="Название организации"
    )
    organization_logo = models.ImageField(
        upload_to="settings/", blank=True, null=True, verbose_name="Логотип организации"
    )
    organization_description = models.TextField(
        blank=True, verbose_name="Описание организации"
    )

    # Настройки индексации
    robots_txt = models.TextField(blank=True, verbose_name="Содержимое robots.txt")
    sitemap_enabled = models.BooleanField(default=True, verbose_name="Включить sitemap")

    # Активные настройки
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "SEO и аналитика"
        verbose_name_plural = "SEO и аналитика"

    def __str__(self):
        return f"SEO настройки - {self.meta_title or 'Без названия'}"

    def save(self, *args, **kwargs):
        # Обеспечиваем, что только один экземпляр SEO настроек активен
        if self.is_active:
            max_retries = 3
            retry_delay = 0.1

            for attempt in range(max_retries):
                try:
                    # Исключаем текущий объект из обновления, если он уже существует
                    queryset = SEOSettings.objects.filter(is_active=True)
                    if self.pk:
                        queryset = queryset.exclude(pk=self.pk)
                    queryset.update(is_active=False)
                    break
                except Exception:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    # Если все попытки неудачны, продолжаем сохранение
                    pass

        super().save(*args, **kwargs)
        # Инвалидируем кэш SEO настроек
        from django.core.cache import cache

        cache.delete("seo_settings_active")
