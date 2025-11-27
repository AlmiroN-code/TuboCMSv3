"""
Models for ads system.
"""
import time
import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import F
from django.utils.text import slugify

User = get_user_model()


class AdPlacement(models.Model):
    """Model for ad placement locations."""

    PLACEMENT_TYPES = [
        ("banner", "Баннер"),
        ("sidebar", "Боковая панель"),
        ("header", "Заголовок"),
        ("footer", "Подвал"),
        ("popup", "Всплывающее окно"),
        ("video_overlay", "Наложение на видео"),
        ("in_content", "Внутри контента"),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="Название")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Слаг")
    placement_type = models.CharField(
        max_length=20, choices=PLACEMENT_TYPES, verbose_name="Тип размещения"
    )
    width = models.PositiveIntegerField(verbose_name="Ширина (px)")
    height = models.PositiveIntegerField(verbose_name="Высота (px)")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Место размещения"
        verbose_name_plural = "Места размещения"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class AdCampaign(models.Model):
    """Model for ad campaigns."""

    STATUS_CHOICES = [
        ("draft", "Черновик"),
        ("active", "Активная"),
        ("paused", "Приостановлена"),
        ("completed", "Завершена"),
        ("cancelled", "Отменена"),
    ]

    name = models.CharField(max_length=200, verbose_name="Название кампании")
    advertiser = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ad_campaigns",
        verbose_name="Рекламодатель",
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    budget = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Бюджет"
    )
    start_date = models.DateTimeField(verbose_name="Дата начала")
    end_date = models.DateTimeField(verbose_name="Дата окончания")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name="Статус"
    )
    target_impressions = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Целевые показы"
    )
    target_clicks = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Целевые клики"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Рекламная кампания"
        verbose_name_plural = "Рекламные кампании"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class AdBanner(models.Model):
    """Model for ad banners."""

    BANNER_TYPES = [
        ("image", "Изображение"),
        ("video", "Видео"),
        ("html", "HTML"),
        ("text", "Текст"),
    ]

    name = models.CharField(max_length=200, verbose_name="Название баннера")
    campaign = models.ForeignKey(
        AdCampaign,
        on_delete=models.CASCADE,
        related_name="banners",
        verbose_name="Кампания",
    )
    placement = models.ForeignKey(
        AdPlacement,
        on_delete=models.CASCADE,
        related_name="banners",
        verbose_name="Место размещения",
    )
    banner_type = models.CharField(
        max_length=20, choices=BANNER_TYPES, verbose_name="Тип баннера"
    )

    # Content fields
    image = models.ImageField(
        upload_to="ads/images/", blank=True, null=True, verbose_name="Изображение"
    )
    video = models.FileField(
        upload_to="ads/videos/", blank=True, null=True, verbose_name="Видео"
    )
    html_content = models.TextField(blank=True, verbose_name="HTML контент")
    text_content = models.TextField(blank=True, verbose_name="Текстовый контент")

    # Link and tracking
    target_url = models.URLField(verbose_name="Целевая ссылка")
    alt_text = models.CharField(
        max_length=200, blank=True, verbose_name="Альтернативный текст"
    )

    # Display settings
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    priority = models.PositiveIntegerField(default=0, verbose_name="Приоритет")
    weight = models.PositiveIntegerField(default=1, verbose_name="Вес (для ротации)")

    # Tracking
    impressions_count = models.PositiveIntegerField(
        default=0, verbose_name="Количество показов"
    )
    clicks_count = models.PositiveIntegerField(
        default=0, verbose_name="Количество кликов"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Рекламный баннер"
        verbose_name_plural = "Рекламные баннеры"
        ordering = ["-priority", "-created_at"]

    def __str__(self):
        return self.name

    @property
    def ctr(self):
        """Click-through rate."""
        if self.impressions_count == 0:
            return 0
        return (self.clicks_count / self.impressions_count) * 100

    def record_impression(self):
        """Record an impression with retry logic to handle SQLite locks."""
        max_retries = 3
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                # Используем F() для атомарного обновления без блокировок
                AdBanner.objects.filter(pk=self.pk).update(
                    impressions_count=F("impressions_count") + 1
                )
                # Обновляем локальный объект
                self.refresh_from_db()
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                # Если все попытки неудачны, просто игнорируем ошибку
                # чтобы не ломать работу сайта
                pass

    def record_click(self):
        """Record a click with retry logic to handle SQLite locks."""
        max_retries = 3
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                # Используем F() для атомарного обновления без блокировок
                AdBanner.objects.filter(pk=self.pk).update(
                    clicks_count=F("clicks_count") + 1
                )
                # Обновляем локальный объект
                self.refresh_from_db()
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
                # Если все попытки неудачны, просто игнорируем ошибку
                pass


class AdImpression(models.Model):
    """Model for tracking ad impressions."""

    banner = models.ForeignKey(
        AdBanner,
        on_delete=models.CASCADE,
        related_name="impressions",
        verbose_name="Баннер",
    )
    ip_address = models.GenericIPAddressField(verbose_name="IP адрес")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    referer = models.URLField(blank=True, verbose_name="Реферер")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Показ рекламы"
        verbose_name_plural = "Показы рекламы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Показ {self.banner.name} - {self.created_at}"


class AdClick(models.Model):
    """Model for tracking ad clicks."""

    banner = models.ForeignKey(
        AdBanner, on_delete=models.CASCADE, related_name="clicks", verbose_name="Баннер"
    )
    ip_address = models.GenericIPAddressField(verbose_name="IP адрес")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    referer = models.URLField(blank=True, verbose_name="Реферер")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Клик по рекламе"
        verbose_name_plural = "Клики по рекламе"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Клик {self.banner.name} - {self.created_at}"


class AdZone(models.Model):
    """Model for ad zones (grouped placements)."""

    name = models.CharField(max_length=100, unique=True, verbose_name="Название зоны")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Слаг")
    description = models.TextField(blank=True, verbose_name="Описание")
    placements = models.ManyToManyField(
        AdPlacement, related_name="zones", verbose_name="Места размещения"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Рекламная зона"
        verbose_name_plural = "Рекламные зоны"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
