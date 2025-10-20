"""
Celery tasks for video processing.
"""
from celery import shared_task
from django.conf import settings
from .models import Video
from .services import VideoProcessingService
from .services_encoding import VideoProcessingService as EncodingService


@shared_task(bind=True)
def process_video_async(self, video_id, selected_profiles=None):
    """Process video asynchronously."""
    try:
        video = Video.objects.get(id=video_id)
        
        # Update task progress
        self.update_state(
            state='PROGRESS',
            meta={'progress': 10, 'status': 'Starting processing...'}
        )
        
        # Process video with new encoding system
        success = EncodingService.process_video(video_id, selected_profiles)
        
        if success:
            # Update video status to published
            video.status = 'published'
            video.is_published = True
            video.save(update_fields=['status', 'is_published'])
            
            # Update task progress
            self.update_state(
                state='SUCCESS',
                meta={'progress': 100, 'status': 'Processing completed and video published!'}
            )
            
            # Send notification to user
            send_processing_complete_notification.delay(video_id)
            
        else:
            # Update task progress
            self.update_state(
                state='FAILURE',
                meta={'progress': 0, 'status': 'Processing failed!'}
            )
            
    except Video.DoesNotExist:
        self.update_state(
            state='FAILURE',
            meta={'progress': 0, 'status': 'Video not found!'}
        )
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'progress': 0, 'status': f'Error: {str(e)}'}
        )


@shared_task
def send_processing_complete_notification(video_id):
    """Send notification when video processing is complete."""
    try:
        video = Video.objects.get(id=video_id)
        
        # Here you would send email notification to user
        # For now, we'll just log it
        print(f"Video {video.title} processing completed for user {video.user.username}")
        
    except Video.DoesNotExist:
        print(f"Video with id {video_id} not found")


@shared_task
def cleanup_old_videos():
    """Clean up old draft videos that were never published."""
    from django.utils import timezone
    from datetime import timedelta
    
    # Delete draft videos older than 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_drafts = Video.objects.filter(
        status='draft',
        created_at__lt=cutoff_date
    )
    
    count = old_drafts.count()
    old_drafts.delete()
    
    print(f"Cleaned up {count} old draft videos")


@shared_task
def generate_video_thumbnails(video_id):
    """Generate multiple thumbnails for a video."""
    try:
        video = Video.objects.get(id=video_id)
        video_path = video.video_file.path
        
        # Generate thumbnails at different time points
        thumbnail_times = [5, 15, 30, 60]  # seconds
        
        for time_offset in thumbnail_times:
            if time_offset < video.duration:
                thumbnail_path = os.path.join(
                    settings.MEDIA_ROOT,
                    'thumbnails',
                    f'thumb_{video.id}_{time_offset}s.jpg'
                )
                
                VideoProcessingService.generate_thumbnail(
                    video_path, 
                    thumbnail_path, 
                    time_offset
                )
        
    except Video.DoesNotExist:
        print(f"Video with id {video_id} not found")
    except Exception as e:
        print(f"Error generating thumbnails: {e}")


@shared_task
def update_video_statistics():
    """Update video statistics periodically."""
    from django.db.models import Count
    
    # Update view counts
    videos = Video.objects.annotate(
        actual_views=Count('video_views')
    )
    
    for video in videos:
        if video.views_count != video.actual_views:
            video.views_count = video.actual_views
            video.save(update_fields=['views_count'])
    
    print("Video statistics updated")


@shared_task
def compress_video(video_id):
    """Compress video to reduce file size."""
    try:
        video = Video.objects.get(id=video_id)
        video_path = video.video_file.path
        
        # Create compressed version
        compressed_path = video_path.replace('.mp4', '_compressed.mp4')
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-c:v', 'libx264',
            '-crf', '28',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-y',
            compressed_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Replace original with compressed version
            os.replace(compressed_path, video_path)
            print(f"Video {video.title} compressed successfully")
        else:
            print(f"Error compressing video: {result.stderr}")
            
    except Video.DoesNotExist:
        print(f"Video with id {video_id} not found")
    except Exception as e:
        print(f"Error compressing video: {e}")


