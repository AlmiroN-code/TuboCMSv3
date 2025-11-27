"""
Video models for TubeCMS.
"""

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.core.models import Category, Tag, TimeStampedModel
from apps.core.utils import (
    generate_poster_path,
    generate_thumbnail_path,
    generate_video_path,
)

from .managers import VideoManager
from .models_favorites import (
    Favorite,
    Playlist,
    PlaylistFollow,
    PlaylistLike,
    PlaylistVideo,
)

User = get_user_model()


def generate_encoded_video_path(instance, filename):
    """Generate path for encoded video files."""
    return f"videos/{instance.profile.resolution}/{filename}"


class VideoFile(models.Model):
    """Encoded video files for different profiles."""

    video = models.ForeignKey(
        "Video", on_delete=models.CASCADE, related_name="encoded_files"
    )
    profile = models.ForeignKey("VideoEncodingProfile", on_delete=models.CASCADE)
    file = models.FileField(upload_to=generate_encoded_video_path)
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    is_primary = models.BooleanField(
        default=False, help_text="Primary quality for this video"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Video File"
        verbose_name_plural = "Video Files"
        unique_together = ["video", "profile"]

    def __str__(self):
        return f"{self.video.title} - {self.profile.name}"

    def save(self, *args, **kwargs):
        # Ensure only one primary file per video
        if self.is_primary:
            VideoFile.objects.filter(video=self.video, is_primary=True).update(
                is_primary=False
            )
        super().save(*args, **kwargs)


class Video(TimeStampedModel):
    """Video model."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("processing", "Processing"),
        ("published", "Published"),
        ("private", "Private"),
        ("rejected", "Rejected"),
    ]

    # Author is determined by who creates the video (request.user)
    # Stored for reference but not as ForeignKey to User
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_videos",
        verbose_name="Автор",
        help_text="Пользователь, который загрузил видео",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Video file - stores paths to converted files
    temp_video_file = models.FileField(
        upload_to="videos/tmp/",
        blank=True,
        null=True,
        help_text="Временный файл видео до обработки",
        verbose_name="Video file",
    )
    # Converted video files paths (JSON field) - хранит пути к сконвертированным файлам
    converted_files = models.JSONField(
        default=list, blank=True, help_text="Paths to converted video files"
    )
    # Processed files
    preview = models.FileField(
        upload_to="previews/",
        blank=True,
        null=True,
        help_text="Short video preview (12 seconds, 6 segments)",
    )
    poster = models.ImageField(
        upload_to="posters/",
        blank=True,
        null=True,
        help_text="Poster image (250x150px from middle of video)",
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    tags = models.ManyToManyField(Tag, blank=True)
    performers = models.ManyToManyField(
        "models.Model",
        blank=True,
        related_name="videos",
        through="models.ModelVideo",
        verbose_name="Модели",
    )

    # Video metadata
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    resolution = models.CharField(
        max_length=20, blank=True, help_text="e.g., 1920x1080"
    )
    format = models.CharField(max_length=10, blank=True, help_text="e.g., mp4, avi")

    # Status and visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    is_featured = models.BooleanField(default=False)

    # Statistics
    views_count = models.PositiveIntegerField(default=0, verbose_name="Просмотры")
    comments_count = models.PositiveIntegerField(default=0, verbose_name="Комментарии")

    # SEO
    slug = models.SlugField(max_length=250, unique=True, blank=True, null=True)
    meta_description = models.CharField(max_length=160, blank=True)

    # Processing
    processing_status = models.CharField(max_length=20, default="pending")
    processing_progress = models.PositiveIntegerField(default=0)
    processing_error = models.TextField(blank=True)

    # Managers
    objects = VideoManager()

    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videos"
        ordering = ["-created_at"]
        indexes = [
            # Основные индексы для фильтрации
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["status", "is_featured", "created_at"]),
            models.Index(fields=["created_by", "status", "created_at"]),
            models.Index(fields=["category", "status", "created_at"]),
            # Индексы для сортировки
            models.Index(fields=["views_count", "created_at"]),
            models.Index(fields=["-views_count", "-created_at"]),
            # Индексы для поиска
            models.Index(fields=["title"]),
            models.Index(fields=["slug"]),
            # Составные индексы для популярных запросов
            models.Index(fields=["status", "category", "views_count"]),
            models.Index(fields=["status", "is_featured"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            import transliterate
            from django.utils.text import slugify

            # Try to transliterate cyrillic to latin first
            try:
                transliterated_title = transliterate.translit(
                    self.title, "ru", reversed=True
                )
                base_slug = slugify(transliterated_title)
            except:
                # Fallback to regular slugify
                base_slug = slugify(self.title)

            # If slug is still empty, use video ID
            if not base_slug:
                base_slug = f"video-{self.id}" if self.id else "video"

            self.slug = base_slug
            counter = 1
            while Video.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)

    @property
    def primary_video_file(self):
        """Get primary video file."""
        try:
            return self.encoded_files.filter(is_primary=True).first()
        except Exception:
            return None

    @property
    def available_qualities(self):
        """Get available video qualities."""
        return self.encoded_files.filter(profile__is_active=True).order_by(
            "profile__order"
        )

    def get_video_file_by_quality(self, quality):
        """Get video file by quality (e.g., '720p')."""
        try:
            return self.encoded_files.filter(profile__resolution=quality).first()
        except Exception:
            return None

    @property
    def duration_formatted(self):
        """Return formatted duration."""
        hours = self.duration // 3600
        minutes = (self.duration % 3600) // 60
        seconds = self.duration % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def increment_views(self):
        """Increment view count atomically."""
        from django.db.models import F

        Video.objects.filter(pk=self.pk).update(views_count=F("views_count") + 1)
        # Обновляем локальный объект
        self.refresh_from_db()

    @property
    def user(self):
        """Backward compatibility property for created_by."""
        return self.created_by


class VideoLike(TimeStampedModel):
    """Video likes/dislikes."""

    LIKE_CHOICES = [
        (1, "Like"),
        (-1, "Dislike"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="video_likes")
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="likes")
    value = models.SmallIntegerField(choices=LIKE_CHOICES)

    class Meta:
        unique_together = ["user", "video"]
        verbose_name = "Video Like"
        verbose_name_plural = "Video Likes"

    def __str__(self):
        return f"{self.user} {'liked' if self.value == 1 else 'disliked'} {self.video}"


class VideoView(TimeStampedModel):
    """Video views tracking."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="video_views"
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)

    class Meta:
        unique_together = ["video", "ip_address", "session_key"]
        verbose_name = "Video View"
        verbose_name_plural = "Video Views"

    def __str__(self):
        return f"View of {self.video} from {self.ip_address}"


class VideoReport(TimeStampedModel):
    """Video reports."""

    REPORT_TYPES = [
        ("spam", "Spam"),
        ("inappropriate", "Inappropriate Content"),
        ("violence", "Violence"),
        ("harassment", "Harassment"),
        ("copyright", "Copyright Infringement"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="video_reports"
    )
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="reports")
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        unique_together = ["user", "video"]
        verbose_name = "Video Report"
        verbose_name_plural = "Video Reports"

    def __str__(self):
        return f"Report of {self.video} by {self.user}"


class Rating(TimeStampedModel):
    """Rating model for videos (like/dislike)."""

    RATING_CHOICES = [
        (1, "Like"),
        (-1, "Dislike"),
    ]

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="video_ratings",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    value = models.SmallIntegerField(choices=RATING_CHOICES)

    class Meta:
        verbose_name = "Rating"
        verbose_name_plural = "Ratings"
        indexes = [
            models.Index(fields=["video", "value"]),
            models.Index(fields=["video", "user"]),
            models.Index(fields=["video", "ip_address"]),
        ]

    def clean(self):
        """Validate that either user or ip_address is set."""
        from django.core.exceptions import ValidationError

        if not self.user and not self.ip_address:
            raise ValidationError("Either user or ip_address must be set.")
        if self.user and self.ip_address:
            raise ValidationError("Cannot set both user and ip_address.")

    def save(self, *args, **kwargs):
        """Override save to enforce unique constraints."""
        self.clean()

        # Check for existing rating
        if self.user:
            existing = Rating.objects.filter(video=self.video, user=self.user).exclude(
                pk=self.pk if self.pk else None
            )
            if existing.exists():
                raise ValueError(
                    f"User {self.user.username} has already rated this video."
                )
        elif self.ip_address:
            existing = Rating.objects.filter(
                video=self.video, ip_address=self.ip_address, user__isnull=True
            ).exclude(pk=self.pk if self.pk else None)
            if existing.exists():
                raise ValueError(f"IP {self.ip_address} has already rated this video.")

        super().save(*args, **kwargs)

    def __str__(self):
        identifier = self.user.username if self.user else self.ip_address
        return f"{identifier} {'liked' if self.value == 1 else 'disliked'} {self.video.title}"


class WatchLater(TimeStampedModel):
    """Список «Посмотреть позже» для пользователя."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watch_later")
    video = models.ForeignKey(
        Video, on_delete=models.CASCADE, related_name="watch_later_entries"
    )

    class Meta:
        verbose_name = "Watch Later"
        verbose_name_plural = "Watch Later"
        unique_together = ["user", "video"]

    def __str__(self):
        return f"{self.user} → {self.video}"


class VideoStream(TimeStampedModel):
    """HLS/DASH streaming information for videos."""
    
    STREAM_TYPE_CHOICES = [
        ("hls", "HLS (HTTP Live Streaming)"),
        ("dash", "DASH (Dynamic Adaptive Streaming)"),
    ]
    
    video = models.ForeignKey(
        Video, 
        on_delete=models.CASCADE, 
        related_name="streams"
    )
    stream_type = models.CharField(
        max_length=10, 
        choices=STREAM_TYPE_CHOICES,
        help_text="Type of streaming protocol"
    )
    profile = models.ForeignKey(
        "VideoEncodingProfile",
        on_delete=models.CASCADE,
        help_text="Quality profile for this stream"
    )
    manifest_path = models.CharField(
        max_length=500,
        help_text="Path to manifest file (playlist.m3u8 for HLS or manifest.mpd for DASH)"
    )
    segment_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of segments in the stream"
    )
    total_size = models.PositiveIntegerField(
        default=0,
        help_text="Total size of all segments in bytes"
    )
    is_ready = models.BooleanField(
        default=False,
        help_text="Whether the stream is ready for playback"
    )
    
    class Meta:
        verbose_name = "Video Stream"
        verbose_name_plural = "Video Streams"
        unique_together = ["video", "stream_type", "profile"]
        indexes = [
            models.Index(fields=["video", "stream_type"]),
            models.Index(fields=["video", "is_ready"]),
        ]
    
    def __str__(self):
        return f"{self.video.title} - {self.get_stream_type_display()} ({self.profile.name})"
    
    @property
    def size_mb(self):
        """Get total size in MB."""
        return self.total_size // (1024 * 1024)
