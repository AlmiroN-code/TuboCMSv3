"""
Video models for TubeCMS.
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.core.models import Category, Tag, TimeStampedModel
from apps.core.utils import generate_video_path, generate_thumbnail_path, generate_poster_path

User = get_user_model()


def generate_encoded_video_path(instance, filename):
    """Generate path for encoded video files."""
    return f"videos/{instance.profile.resolution}/{filename}"


class VideoFile(models.Model):
    """Encoded video files for different profiles."""
    video = models.ForeignKey('Video', on_delete=models.CASCADE, related_name='encoded_files')
    profile = models.ForeignKey('VideoEncodingProfile', on_delete=models.CASCADE)
    file = models.FileField(upload_to=generate_encoded_video_path)
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    is_primary = models.BooleanField(default=False, help_text="Primary quality for this video")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Video File"
        verbose_name_plural = "Video Files"
        unique_together = ['video', 'profile']

    def __str__(self):
        return f"{self.video.title} - {self.profile.name}"

    def save(self, *args, **kwargs):
        # Ensure only one primary file per video
        if self.is_primary:
            VideoFile.objects.filter(video=self.video, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class Video(TimeStampedModel):
    """Video model."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('published', 'Published'),
        ('private', 'Private'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Video file - stores paths to converted files
    temp_video_file = models.FileField(upload_to='videos/tmp/', blank=True, null=True, help_text="Video file (converted versions)", verbose_name="Video file")
    # Converted video files paths (JSON field)
    converted_files = models.JSONField(default=list, blank=True, help_text="Paths to converted video files")
    # Processed files
    preview = models.FileField(upload_to='previews/', blank=True, null=True, help_text="Short video preview")
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    performers = models.ManyToManyField('models.Model', blank=True, related_name='videos', through='models.ModelVideo')
    
    # Video metadata
    duration = models.PositiveIntegerField(default=0, help_text="Duration in seconds")
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    resolution = models.CharField(max_length=20, blank=True, help_text="e.g., 1920x1080")
    format = models.CharField(max_length=10, blank=True, help_text="e.g., mp4, avi")
    
    # Status and visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_premium = models.BooleanField(default=False)
    
    # Statistics
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    dislikes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    
    # SEO
    slug = models.SlugField(max_length=250, unique=True, blank=True, null=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    # Processing
    processing_status = models.CharField(max_length=20, default='pending')
    processing_progress = models.PositiveIntegerField(default=0)
    processing_error = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videos"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'is_published']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['views_count']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            import transliterate
            
            # Try to transliterate cyrillic to latin first
            try:
                transliterated_title = transliterate.translit(self.title, 'ru', reversed=True)
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
        except:
            return None

    @property
    def available_qualities(self):
        """Get available video qualities."""
        return self.encoded_files.filter(profile__is_active=True).order_by('profile__order')

    def get_video_file_by_quality(self, quality):
        """Get video file by quality (e.g., '720p')."""
        try:
            return self.encoded_files.filter(profile__resolution=quality).first()
        except:
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

    @property
    def file_size_formatted(self):
        """Return formatted file size."""
        if self.file_size == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = self.file_size
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"

    def increment_views(self):
        """Increment view count."""
        self.views_count += 1
        self.save(update_fields=['views_count'])


class VideoLike(TimeStampedModel):
    """Video likes/dislikes."""
    LIKE_CHOICES = [
        (1, 'Like'),
        (-1, 'Dislike'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_likes')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='likes')
    value = models.SmallIntegerField(choices=LIKE_CHOICES)
    
    class Meta:
        unique_together = ['user', 'video']
        verbose_name = "Video Like"
        verbose_name_plural = "Video Likes"

    def __str__(self):
        return f"{self.user} {'liked' if self.value == 1 else 'disliked'} {self.video}"


class VideoView(TimeStampedModel):
    """Video views tracking."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='video_views')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    
    class Meta:
        unique_together = ['video', 'ip_address', 'session_key']
        verbose_name = "Video View"
        verbose_name_plural = "Video Views"

    def __str__(self):
        return f"View of {self.video} from {self.ip_address}"


class VideoReport(TimeStampedModel):
    """Video reports."""
    REPORT_TYPES = [
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('violence', 'Violence'),
        ('harassment', 'Harassment'),
        ('copyright', 'Copyright Infringement'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_reports')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'video']
        verbose_name = "Video Report"
        verbose_name_plural = "Video Reports"

    def __str__(self):
        return f"Report of {self.video} by {self.user}"

