"""
Signals for video model.
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.conf import settings
from .models import Video
from .tasks import process_video_async, cleanup_old_videos


@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    """Handle video post-save events."""
    # Only process when video is first created with temp_video_file
    if created and instance.temp_video_file:
        # Get selected encoding profiles from form
        selected_profiles = getattr(instance, '_selected_encoding_profiles', None)
        
        print(f"Starting async processing for video {instance.id}")
        # Process video asynchronously
        process_video_async.delay(instance.id, selected_profiles)
        
        # Update user's video count
        instance.user.videos_count += 1
        instance.user.save(update_fields=['videos_count'])
    
    # Slug is handled in the model's save method


@receiver(pre_delete, sender=Video)
def video_pre_delete(sender, instance, **kwargs):
    """Handle video pre-delete events."""
    # Update user's video count
    if instance.user.videos_count > 0:
        instance.user.videos_count -= 1
        instance.user.save(update_fields=['videos_count'])
    
    # Delete associated files
    try:
        if instance.video_file:
            instance.video_file.delete(save=False)
        if instance.thumbnail:
            instance.thumbnail.delete(save=False)
        if instance.poster:
            instance.poster.delete(save=False)
    except Exception as e:
        print(f"Error deleting video files: {e}")


# Periodic tasks
from celery import shared_task

@shared_task
def periodic_cleanup():
    """Periodic cleanup task."""
    cleanup_old_videos.delay()


