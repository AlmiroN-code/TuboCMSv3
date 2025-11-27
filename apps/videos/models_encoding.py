"""
Video encoding models for TubeCMS.
"""
import time

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class VideoEncodingProfile(models.Model):
    """Video encoding profiles (360p, 720p, 1080p, etc.)."""

    name = models.CharField(max_length=50, unique=True)
    resolution = models.CharField(max_length=20, help_text="e.g., 360p, 720p, 1080p")
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    bitrate = models.PositiveIntegerField(help_text="Bitrate in kbps")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Video Encoding Profile"
        verbose_name_plural = "Video Encoding Profiles"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} ({self.resolution})"

    @property
    def folder_name(self):
        """Get folder name for this profile."""
        return f"{self.resolution}"


class MetadataExtractionSettings(models.Model):
    """Settings for metadata extraction (poster, preview)."""

    # Poster settings
    poster_width = models.PositiveIntegerField(default=250)
    poster_height = models.PositiveIntegerField(default=150)
    poster_format = models.CharField(max_length=10, default="JPEG")
    poster_quality = models.PositiveIntegerField(
        default=85, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )

    # Preview settings
    preview_width = models.PositiveIntegerField(default=250)
    preview_height = models.PositiveIntegerField(default=150)
    preview_duration = models.PositiveIntegerField(
        default=12, help_text="Duration in seconds"
    )
    preview_segment_duration = models.PositiveIntegerField(
        default=2, help_text="Segment duration in seconds"
    )
    preview_format = models.CharField(max_length=10, default="MP4")
    preview_quality = models.PositiveIntegerField(
        default=85, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )

    # General settings
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Metadata Extraction Settings"
        verbose_name_plural = "Metadata Extraction Settings"

    def __str__(self):
        return "Metadata Extraction Settings"

    def save(self, *args, **kwargs):
        # Ensure only one active settings instance
        if self.is_active:
            max_retries = 3
            retry_delay = 0.1

            for attempt in range(max_retries):
                try:
                    # Исключаем текущий объект из обновления, если он уже существует
                    queryset = MetadataExtractionSettings.objects.filter(is_active=True)
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
