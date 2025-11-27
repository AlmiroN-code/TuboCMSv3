from django.contrib import admin, messages
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import admin


from .forms_admin import VideoAdminForm
from .models import Rating, Video, VideoLike, VideoReport, VideoView, VideoStream
from .tasks import process_video_async


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    form = VideoAdminForm    # WYSIWYG редактор для текстовых полей

    list_display = (
        "title",
        "created_by",
        "category",
        "status",
        "views_count",
        "preview_display",
        "created_at",
    )
    list_filter = ("status", "category", "created_at", "updated_at")
    search_fields = ("title", "description", "created_by__username", "tags__name")
    readonly_fields = (
        "created_at",
        "updated_at",
        "duration",
        "converted_files_display",
        "performers_display",
        "processing_status_display",
        "processing_error",
    )
    filter_horizontal = ("tags",)
    actions = ["start_processing"]

    fieldsets = (
        (
            "Основная информация",
            {
                "fields": (
                    "title",
                    "description",
                    "created_by",
                    "category",
                    "tags_input",
                    "tags",
                )
            },
        ),
        (
            "Медиа файлы",
            {
                "fields": (
                    "temp_video_file",
                    "preview",
                    "poster",
                    "encoding_profiles",
                    "converted_files_display",
                )
            },
        ),
        ("Настройки", {"fields": ("status", "is_featured")}),
        (
            "Статистика",
            {"fields": ("views_count", "duration"), "classes": ("collapse",)},
        ),
        (
            "Обработка",
            {
                "fields": (
                    "processing_status_display",
                    "processing_error",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Информация о моделях",
            {
                "fields": ("performers_display",),
                "classes": ("collapse",),
            },
        ),
        ("Даты", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def preview_display(self, obj):
        if obj.preview:
            return format_html(
                '<video width="100" height="60" controls><source src="{}" type="video/mp4"></video>',
                obj.preview.url,
            )
        return "No Preview"

    preview_display.short_description = "Preview"

    def encoded_files_display(self, obj):
        """Display encoded video files."""
        if not obj.pk:
            return "Save video first"

        files = obj.encoded_files.all()
        if not files:
            return "No encoded files"

        html = "<ul>"
        for vf in files:
            html += f"<li><strong>{vf.profile.name}</strong> ({vf.profile.resolution}) - {vf.file_size // 1024 // 1024}MB"
            if vf.is_primary:
                html += " <span style='color: green;'>[PRIMARY]</span>"
            html += "</li>"
        html += "</ul>"
        return format_html(html)

    encoded_files_display.short_description = "Encoded Files"

    def converted_files_display(self, obj):
        """Display converted files from JSON field."""
        if not obj.converted_files:
            return "No converted files"

        html = "<ul>"
        for file_path in obj.converted_files:
            # Extract resolution from path
            resolution = file_path.split("/")[-2] if "/" in file_path else "Unknown"
            html += f"<li><strong>{resolution}</strong> - {file_path}</li>"
        html += "</ul>"
        return format_html(html)

    converted_files_display.short_description = "Converted Files"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("created_by", "category")
            .prefetch_related("tags", "performers")
        )

    def performers_display(self, obj):
        """Display performers for this video."""
        if obj.pk:
            performers = obj.performers.all()
            if performers:
                return ", ".join(
                    [
                        f"{p.display_name} ({'основная' if p.model_videos.filter(video=obj, is_primary=True).exists() else 'участница'})"
                        for p in performers
                    ]
                )
            else:
                return "Нет моделей"
        return "Сохраните видео для отображения моделей"

    performers_display.short_description = "Модели"

    def processing_status_display(self, obj):
        """Display processing status with progress bar."""
        if not obj.pk:
            return "Сохраните видео"
        
        status_colors = {
            "pending": "#fbbf24",      # yellow
            "processing": "#3b82f6",   # blue  
            "completed": "#10b981",    # green
            "failed": "#ef4444",       # red
            "error": "#ef4444",        # red
        }
        
        status_labels = {
            "pending": "Ожидает",
            "processing": "Обрабатывается", 
            "completed": "Завершено",
            "failed": "Ошибка",
            "error": "Ошибка",
        }
        
        color = status_colors.get(obj.processing_status, "#6b7280")
        label = status_labels.get(obj.processing_status, obj.processing_status)
        
        html = f'<span style="color: {color}; font-weight: bold;">{label}</span>'
        
        if obj.processing_status == "processing":
            progress = obj.processing_progress or 0
            html += f'<br><div style="width: 200px; height: 8px; background: #e5e7eb; border-radius: 4px; margin-top: 4px;">'
            html += f'<div style="width: {progress}%; height: 100%; background: {color}; border-radius: 4px;"></div></div>'
            html += f'<small style="color: #6b7280;">{progress}%</small>'
            
            # Add auto-refresh for processing videos
            html += f'''
            <script>
            (function() {{
                if (document.querySelector('[data-video-{obj.id}-refresh]')) return;
                const marker = document.createElement('div');
                marker.setAttribute('data-video-{obj.id}-refresh', 'true');
                marker.style.display = 'none';
                document.body.appendChild(marker);
                
                const refreshProgress = () => {{
                    fetch('/videos/api/progress/{obj.id}/')
                        .then(r => r.json())
                        .then(data => {{
                            if (data.processing_status !== 'processing') {{
                                location.reload();
                            }}
                        }})
                        .catch(() => {{}});
                }};
                
                const interval = setInterval(() => {{
                    if (!document.body.contains(marker)) {{
                        clearInterval(interval);
                        return;
                    }}
                    refreshProgress();
                }}, 3000);
            }})();
            </script>
            '''
        
        return format_html(html)

    processing_status_display.short_description = "Статус обработки"

    def save_model(self, request, obj, form, change):
        """Override save_model to ensure processing starts also when file added or changed.

        Note: Processing is triggered by the post_save signal, so we don't need to trigger it here.
        This method is kept for backward compatibility and potential future use.
        """
        # Save the model - the signal will handle processing
        super().save_model(request, obj, form, change)

    def start_processing(self, request, queryset):
        """Admin action: Start processing for selected videos."""
        from .models_encoding import VideoEncodingProfile

        processed_count = 0
        skipped_count = 0
        error_count = 0

        for video in queryset:
            # Check if video has a file
            if not video.temp_video_file:
                skipped_count += 1
                messages.warning(
                    request,
                    f'Video "{video.title}" (ID: {video.id}) skipped: no video file',
                )
                continue

            # Check if video is already processing or completed
            if video.processing_status in ["processing", "completed"]:
                skipped_count += 1
                messages.info(
                    request,
                    f'Video "{video.title}" (ID: {video.id}) skipped: already {video.processing_status}',
                )
                continue

            # Check if file exists
            try:
                file_exists = video.temp_video_file.storage.exists(
                    video.temp_video_file.name
                )
            except:
                try:
                    import os

                    file_exists = os.path.exists(video.temp_video_file.path)
                except:
                    file_exists = False

            if not file_exists:
                skipped_count += 1
                messages.warning(
                    request,
                    f'Video "{video.title}" (ID: {video.id}) skipped: file does not exist',
                )
                continue

            # Set processing status
            video.processing_status = "processing"
            video.save(update_fields=["processing_status"])

            # Get selected profiles (use all active if none selected)
            selected_profiles = None
            if (
                hasattr(video, "_selected_encoding_profiles")
                and video._selected_encoding_profiles
            ):
                selected_profiles = video._selected_encoding_profiles
            else:
                # Use all active profiles
                selected_profiles = list(
                    VideoEncodingProfile.objects.filter(is_active=True).values_list(
                        "id", flat=True
                    )
                )

            # Start processing task
            try:
                result = process_video_async.delay(video.id, selected_profiles)
                processed_count += 1
                messages.success(
                    request,
                    f'Video "{video.title}" (ID: {video.id}) processing started (task: {result.id})',
                )
            except Exception as e:
                error_count += 1
                video.processing_status = "pending"
                video.save(update_fields=["processing_status"])
                messages.error(
                    request,
                    f'Video "{video.title}" (ID: {video.id}) failed to start processing: {str(e)}',
                )

        # Summary message
        if processed_count > 0:
            messages.success(
                request,
                f"Successfully started processing for {processed_count} video(s)",
            )
        if skipped_count > 0:
            messages.info(
                request,
                f"Skipped {skipped_count} video(s) (already processing/completed or no file)",
            )
        if error_count > 0:
            messages.error(
                request, f"Failed to start processing for {error_count} video(s)"
            )

    start_processing.short_description = "Запустить обработку для выбранных видео"


@admin.register(VideoView)
class VideoViewAdmin(admin.ModelAdmin):
    list_display = ("video", "user", "ip_address", "created_at")
    list_filter = ("created_at",)
    search_fields = ("video__title", "user__username", "ip_address")
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("video", "user")


@admin.register(VideoLike)
class VideoLikeAdmin(admin.ModelAdmin):
    list_display = ("video", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("video__title", "user__username")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("video", "user")


@admin.register(VideoReport)
class VideoReportAdmin(admin.ModelAdmin):
    list_display = ("video", "user", "report_type", "created_at", "is_resolved")
    list_filter = ("report_type", "is_resolved", "created_at")
    search_fields = ("video__title", "user__username", "description")
    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("video", "user")


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("video", "user", "ip_address", "value", "created_at")
    list_filter = ("value", "created_at")
    search_fields = ("video__title", "user__username", "ip_address")
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("video", "user")


# Alert System Admin
from .models_alerts import AlertRule, Alert, SystemMetric


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'alert_type',
        'threshold_value',
        'severity',
        'is_active',
        'check_interval_minutes',
        'cooldown_minutes',
    )
    list_filter = ('alert_type', 'severity', 'is_active')
    search_fields = ('name', 'email_recipients')
    
    fieldsets = (
        ('Rule Configuration', {
            'fields': (
                'name',
                'alert_type',
                'threshold_value',
                'severity',
                'is_active',
            )
        }),
        ('Timing', {
            'fields': (
                'check_interval_minutes',
                'cooldown_minutes',
            )
        }),
        ('Notifications', {
            'fields': (
                'send_email',
                'email_recipients',
                'webhook_url',
            )
        }),
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'rule',
        'status',
        'current_value',
        'created_at',
        'age_display',
        'email_sent',
        'webhook_sent',
    )
    list_filter = ('status', 'rule__alert_type', 'rule__severity', 'created_at')
    search_fields = ('message', 'rule__name')
    readonly_fields = (
        'rule',
        'message',
        'current_value',
        'metadata',
        'created_at',
        'updated_at',
        'email_sent',
        'webhook_sent',
        'resolved_at',
        'acknowledged_at',
        'acknowledged_by',
    )
    actions = ['acknowledge_alerts', 'resolve_alerts']
    
    def age_display(self, obj):
        """Display alert age in human-readable format."""
        minutes = obj.age_minutes
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h"
        days = hours // 24
        return f"{days}d"
    age_display.short_description = 'Age'
    
    def acknowledge_alerts(self, request, queryset):
        """Acknowledge selected alerts."""
        count = 0
        for alert in queryset.filter(status='active'):
            alert.acknowledge(user=request.user)
            count += 1
        self.message_user(request, f"Acknowledged {count} alerts", messages.SUCCESS)
    acknowledge_alerts.short_description = "Acknowledge selected alerts"
    
    def resolve_alerts(self, request, queryset):
        """Resolve selected alerts."""
        count = 0
        for alert in queryset.filter(status__in=['active', 'acknowledged']):
            alert.resolve()
            count += 1
        self.message_user(request, f"Resolved {count} alerts", messages.SUCCESS)
    resolve_alerts.short_description = "Resolve selected alerts"


@admin.register(SystemMetric)
class SystemMetricAdmin(admin.ModelAdmin):
    list_display = (
        'metric_type',
        'value',
        'created_at',
    )
    list_filter = ('metric_type', 'created_at')
    readonly_fields = ('metric_type', 'value', 'metadata', 'created_at')
    
    def has_add_permission(self, request):
        """Metrics are created automatically."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Metrics are read-only."""
        return False



@admin.register(VideoStream)
class VideoStreamAdmin(admin.ModelAdmin):
    list_display = (
        'video',
        'stream_type',
        'profile',
        'segment_count',
        'total_size_display',
        'is_ready',
        'created_at',
    )
    list_filter = ('stream_type', 'is_ready', 'profile')
    search_fields = ('video__title',)
    readonly_fields = (
        'video',
        'stream_type',
        'profile',
        'manifest_path',
        'segment_count',
        'total_size',
        'created_at',
        'updated_at',
    )
    
    def total_size_display(self, obj):
        """Display total size in human-readable format."""
        size_mb = obj.total_size / (1024 * 1024)
        if size_mb < 1024:
            return f"{size_mb:.1f} MB"
        else:
            size_gb = size_mb / 1024
            return f"{size_gb:.2f} GB"
    total_size_display.short_description = 'Size'
    
    def has_add_permission(self, request):
        """Streams are created automatically."""
        return False
