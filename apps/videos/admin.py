from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Video, VideoView, VideoLike, VideoReport
from .forms_admin import VideoAdminForm


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    form = VideoAdminForm
    list_display = ('title', 'user', 'category', 'status', 'views_count', 'likes_count', 'preview_display', 'created_at')
    list_filter = ('status', 'is_published', 'is_premium', 'category', 'created_at', 'updated_at')
    search_fields = ('title', 'description', 'user__username', 'tags__name')
    readonly_fields = ('views_count', 'likes_count', 'created_at', 'updated_at', 'duration', 'file_size', 'encoded_files_display', 'converted_files_display', 'performers_display')
    filter_horizontal = ('tags',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'user', 'category', 'tags')
        }),
        ('Медиа файлы', {
            'fields': ('temp_video_file', 'preview', 'poster')
        }),
        ('Кодирование', {
            'fields': ('encoding_profiles',),
            'classes': ('collapse',)
        }),
        ('Настройки', {
            'fields': ('status', 'is_published', 'is_premium')
        }),
        ('Статистика', {
            'fields': ('views_count', 'likes_count', 'duration', 'file_size', 'encoded_files_display', 'converted_files_display'),
            'classes': ('collapse',)
        }),
        ('Информация о моделях', {
            'fields': ('performers_display',),
            'classes': ('collapse',),
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def preview_display(self, obj):
        if obj.preview:
            return format_html('<video width="100" height="60" controls><source src="{}" type="video/mp4"></video>', obj.preview.url)
        return "No Preview"
    preview_display.short_description = 'Preview'
    
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
    encoded_files_display.short_description = 'Encoded Files'
    
    def converted_files_display(self, obj):
        """Display converted files from JSON field."""
        if not obj.converted_files:
            return "No converted files"
        
        html = "<ul>"
        for file_path in obj.converted_files:
            # Extract resolution from path
            resolution = file_path.split('/')[-2] if '/' in file_path else 'Unknown'
            html += f"<li><strong>{resolution}</strong> - {file_path}</li>"
        html += "</ul>"
        return format_html(html)
    converted_files_display.short_description = 'Converted Files'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'category').prefetch_related('tags', 'performers')
    
    def performers_display(self, obj):
        """Display performers for this video."""
        if obj.pk:
            performers = obj.performers.all()
            if performers:
                return ', '.join([f"{p.display_name} ({'основная' if p.model_videos.filter(video=obj, is_primary=True).exists() else 'участница'})" for p in performers])
            else:
                return "Нет моделей"
        return "Сохраните видео для отображения моделей"
    performers_display.short_description = 'Модели'
    
    def save_model(self, request, obj, form, change):
        """Override save_model to ensure processing starts."""
        super().save_model(request, obj, form, change)
        
        # If this is a new video with temp_video_file, start processing
        if not change and obj.temp_video_file:
            from .tasks import process_video_async
            from .models_encoding import VideoEncodingProfile
            
            # Get selected encoding profiles from form
            selected_profiles = None
            if hasattr(form, 'cleaned_data') and 'encoding_profiles' in form.cleaned_data:
                selected_profiles = list(form.cleaned_data['encoding_profiles'].values_list('id', flat=True))
            
            print(f"Starting async processing for video {obj.id} from admin")
            process_video_async.delay(obj.id, selected_profiles)


@admin.register(VideoView)
class VideoViewAdmin(admin.ModelAdmin):
    list_display = ('video', 'user', 'ip_address', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('video__title', 'user__username', 'ip_address')
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('video', 'user')


@admin.register(VideoLike)
class VideoLikeAdmin(admin.ModelAdmin):
    list_display = ('video', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('video__title', 'user__username')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('video', 'user')


@admin.register(VideoReport)
class VideoReportAdmin(admin.ModelAdmin):
    list_display = ('video', 'user', 'report_type', 'created_at', 'is_resolved')
    list_filter = ('report_type', 'is_resolved', 'created_at')
    search_fields = ('video__title', 'user__username', 'description')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('video', 'user')
