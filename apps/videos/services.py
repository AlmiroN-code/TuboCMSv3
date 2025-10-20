"""
Business logic services for videos.
"""
import os
import subprocess
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from .models import Video, VideoView, VideoLike
from apps.core.utils import format_duration, format_file_size


class VideoProcessingService:
    """Service for video processing operations."""
    
    @staticmethod
    def extract_metadata(video_path):
        """Extract video metadata using ffprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # Extract duration
                duration = 0
                if 'format' in data and 'duration' in data['format']:
                    duration = int(float(data['format']['duration']))
                
                # Extract resolution
                resolution = ''
                if 'streams' in data and data['streams']:
                    stream = data['streams'][0]
                    if 'width' in stream and 'height' in stream:
                        resolution = f"{stream['width']}x{stream['height']}"
                
                # Extract format
                format_name = ''
                if 'format' in data and 'format_name' in data['format']:
                    format_name = data['format']['format_name']
                
                return {
                    'duration': duration,
                    'resolution': resolution,
                    'format': format_name,
                }
        except Exception as e:
            print(f"Error extracting metadata: {e}")
        
        return {}

    @staticmethod
    def generate_thumbnail(video_path, output_path, time_offset=10):
        """Generate thumbnail from video."""
        try:
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(time_offset),
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return False

    @staticmethod
    def process_video(video_id):
        """Process video after upload."""
        try:
            video = Video.objects.get(id=video_id)
            video.processing_status = 'processing'
            video.save()
            
            video_path = video.video_file.path
            
            # Extract metadata
            metadata = VideoProcessingService.extract_metadata(video_path)
            if metadata:
                video.duration = metadata.get('duration', 0)
                video.resolution = metadata.get('resolution', '')
                video.format = metadata.get('format', '')
                video.file_size = os.path.getsize(video_path)
            
            # Generate thumbnail
            thumbnail_path = os.path.join(
                settings.MEDIA_ROOT,
                'thumbnails',
                f'thumb_{video.id}.jpg'
            )
            
            if VideoProcessingService.generate_thumbnail(video_path, thumbnail_path):
                video.thumbnail.name = f'thumbnails/thumb_{video.id}.jpg'
            
            # Update processing status
            video.processing_status = 'completed'
            video.processing_progress = 100
            video.save()
            
            return True
            
        except Video.DoesNotExist:
            return False
        except Exception as e:
            video.processing_status = 'failed'
            video.processing_error = str(e)
            video.save()
            return False


class VideoViewService:
    """Service for video view tracking."""
    
    @staticmethod
    def track_view(video, request):
        """Track video view."""
        try:
            # Get client info
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            session_key = request.session.session_key
            
            # Check if view already exists
            view_exists = VideoView.objects.filter(
                video=video,
                ip_address=ip_address,
                session_key=session_key
            ).exists()
            
            if not view_exists:
                # Create new view
                VideoView.objects.create(
                    video=video,
                    user=request.user if request.user.is_authenticated else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_key=session_key
                )
                
                # Increment view count
                video.increment_views()
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Error tracking view: {e}")
            return False


class VideoLikeService:
    """Service for video likes/dislikes."""
    
    @staticmethod
    def toggle_like(video, user, value):
        """Toggle like/dislike for video."""
        try:
            like, created = VideoLike.objects.get_or_create(
                video=video,
                user=user,
                defaults={'value': value}
            )
            
            if not created:
                if like.value == value:
                    # Remove like/dislike
                    like.delete()
                    # Update counts
                    if value == 1:
                        video.likes_count = max(0, video.likes_count - 1)
                    else:
                        video.dislikes_count = max(0, video.dislikes_count - 1)
                else:
                    # Change like/dislike
                    old_value = like.value
                    like.value = value
                    like.save()
                    
                    # Update counts
                    if old_value == 1:
                        video.likes_count = max(0, video.likes_count - 1)
                    else:
                        video.dislikes_count = max(0, video.dislikes_count - 1)
                    
                    if value == 1:
                        video.likes_count += 1
                    else:
                        video.dislikes_count += 1
            else:
                # New like/dislike
                if value == 1:
                    video.likes_count += 1
                else:
                    video.dislikes_count += 1
            
            video.save(update_fields=['likes_count', 'dislikes_count'])
            
            return {
                'likes_count': video.likes_count,
                'dislikes_count': video.dislikes_count,
                'user_like': value if created or like.value == value else 0
            }
            
        except Exception as e:
            print(f"Error toggling like: {e}")
            return None


class VideoSearchService:
    """Service for video search functionality."""
    
    @staticmethod
    def search_videos(query, filters=None):
        """Search videos with filters."""
        from .models import Video
        
        videos = Video.objects.published()
        
        if query:
            videos = videos.filter(
                models.Q(title__icontains=query) |
                models.Q(description__icontains=query) |
                models.Q(tags__name__icontains=query)
            ).distinct()
        
        if filters:
            if 'category' in filters and filters['category']:
                videos = videos.filter(category__slug=filters['category'])
            
            if 'duration_min' in filters and filters['duration_min']:
                videos = videos.filter(duration__gte=filters['duration_min'])
            
            if 'duration_max' in filters and filters['duration_max']:
                videos = videos.filter(duration__lte=filters['duration_max'])
            
            if 'date_from' in filters and filters['date_from']:
                videos = videos.filter(created_at__gte=filters['date_from'])
            
            if 'date_to' in filters and filters['date_to']:
                videos = videos.filter(created_at__lte=filters['date_to'])
        
        return videos










