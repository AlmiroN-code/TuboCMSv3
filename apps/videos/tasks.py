"""
Celery tasks for video processing.
"""

import os
import subprocess

from celery import shared_task
from django.conf import settings

from .models import Video
from .services_encoding import VideoProcessingService as EncodingService


@shared_task(bind=True)
def process_video_async(self, video_id, selected_profiles=None):
    """Process video asynchronously with proper error handling and logging."""
    import logging
    import traceback

    logger = logging.getLogger(__name__)

    try:
        video = Video.objects.get(id=video_id)

        # Update task progress
        self.update_state(
            state="PROGRESS", meta={"progress": 10, "status": "Starting processing..."}
        )
        logger.info(f"Starting video processing for video {video_id}")

        # Progress callback for Celery task updates
        def progress_callback(percent, status):
            self.update_state(
                state="PROGRESS", 
                meta={"progress": percent, "status": status}
            )

        # Process video with new encoding system
        success = EncodingService.process_video(
            video_id, 
            selected_profiles, 
            progress_callback=progress_callback
        )

        if success:
            # Refresh video object to get latest processing_status
            video.refresh_from_db()

            # Status should already be set to 'published' by EncodingService
            # Just verify and log
            if video.status != "published":
                video.status = "published"
                video.save(update_fields=["status"])

            # Update task progress
            self.update_state(
                state="SUCCESS",
                meta={
                    "progress": 100,
                    "status": "Processing completed and video published!",
                },
            )

            logger.info(f"Video {video_id} processing completed successfully")

            # Send notification to user
            try:
                send_processing_complete_notification.delay(video_id)
            except Exception as notif_error:
                logger.warning(
                    f"Failed to send notification for video {video_id}: {notif_error}"
                )

        else:
            # Refresh video object to get latest processing_status and error
            video.refresh_from_db()

            # Update task progress
            error_msg = (
                video.processing_error
                if video.processing_error
                else "Processing failed!"
            )
            self.update_state(
                state="FAILURE", meta={"progress": 0, "status": error_msg}
            )

            logger.error(f"Video {video_id} processing failed. Error: {error_msg}")
            print(f"[TASK] Video {video_id} processing failed. Error: {error_msg}")

    except Video.DoesNotExist:
        error_msg = f"Video {video_id} not found!"
        logger.error(error_msg)
        self.update_state(state="FAILURE", meta={"progress": 0, "status": error_msg})
        print(f"[TASK] {error_msg}")

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        error_traceback = traceback.format_exc()

        logger.error(f"Video {video_id} processing error: {error_msg}", exc_info=True)

        # Try to update video status and error
        try:
            video = Video.objects.get(id=video_id)
            video.processing_status = "error"
            video.processing_error = f"{error_msg}\n\n{error_traceback}"
            video.status = "draft"  # Keep as draft if processing failed
            video.save(
                update_fields=["processing_status", "processing_error", "status"]
            )
        except Exception as save_error:
            logger.error(
                f"Failed to update video error status for video {video_id}: {save_error}",
                exc_info=True,
            )

        self.update_state(state="FAILURE", meta={"progress": 0, "status": error_msg})
        print(f"[TASK] Video {video_id} processing error: {error_msg}")
        print(f"[TASK] Traceback: {error_traceback}")


@shared_task
def send_processing_complete_notification(video_id):
    """Send notification when video processing is complete."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        video = Video.objects.get(id=video_id)

        # Here you would send email notification to user
        # For now, we'll just log it
        username = video.created_by.username if video.created_by else "Unknown"
        logger.info(f"Video {video.title} processing completed for user {username}")
        print(f"Video {video.title} processing completed for user {username}")

    except Video.DoesNotExist:
        error_msg = f"Video with id {video_id} not found"
        logger.error(error_msg)
        print(error_msg)
    except Exception as e:
        logger.error(
            f"Error sending notification for video {video_id}: {e}", exc_info=True
        )


@shared_task
def cleanup_old_videos():
    """Clean up old draft videos that were never published."""
    from datetime import timedelta

    from django.utils import timezone

    # Delete draft videos older than 30 days
    cutoff_date = timezone.now() - timedelta(days=30)

    old_drafts = Video.objects.filter(status="draft", created_at__lt=cutoff_date)

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
                    "thumbnails",
                    f"thumb_{video.id}_{time_offset}s.jpg",
                )

                VideoProcessingService.generate_thumbnail(
                    video_path, thumbnail_path, time_offset
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
    videos = Video.objects.annotate(actual_views=Count("video_views"))

    for video in videos:
        if video.views_count != video.actual_views:
            video.views_count = video.actual_views
            video.save(update_fields=["views_count"])

    print("Video statistics updated")


@shared_task
def compress_video(video_id):
    """Compress video to reduce file size."""
    try:
        video = Video.objects.get(id=video_id)
        video_path = video.video_file.path

        # Create compressed version
        compressed_path = video_path.replace(".mp4", "_compressed.mp4")

        cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-c:v",
            "libx264",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-y",
            compressed_path,
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


@shared_task
def process_pending_videos(limit: int = 20):
    """
    Подбирает видео для обработки и ставит их в очередь.
    
    Обрабатывает:
    1. Видео в статусе 'pending' с файлом
    2. "Застрявшие" видео в статусе 'processing' более 2 часов
    
    Запускается каждую минуту через Celery Beat.
    """
    import logging
    from datetime import timedelta
    from django.db.models import Q
    from django.utils import timezone
    
    logger = logging.getLogger(__name__)
    
    started = 0
    skipped = 0
    reset = 0
    
    # 1. Сбрасываем "застрявшие" видео (processing > 2 часов)
    stuck_cutoff = timezone.now() - timedelta(hours=2)
    stuck_videos = Video.objects.filter(
        processing_status="processing",
        updated_at__lt=stuck_cutoff
    )
    for video in stuck_videos:
        video.processing_status = "pending"
        video.processing_error = "Reset: stuck in processing for >2 hours"
        video.save(update_fields=["processing_status", "processing_error", "updated_at"])
        reset += 1
        logger.warning(f"Reset stuck video {video.id}")
    
    # 2. Находим видео для обработки
    candidates = (
        Video.objects.filter(processing_status="pending")
        .exclude(Q(temp_video_file__isnull=True) | Q(temp_video_file=""))
        .order_by("created_at")[:limit]
    )

    for video in candidates:
        # Проверяем существование файла
        file_exists = False
        try:
            if video.temp_video_file:
                file_exists = video.temp_video_file.storage.exists(
                    video.temp_video_file.name
                )
        except Exception:
            try:
                import os
                file_exists = os.path.exists(video.temp_video_file.path)
            except Exception:
                file_exists = False

        if not file_exists:
            skipped += 1
            continue

        # Ставим статус processing
        Video.objects.filter(pk=video.pk).update(
            processing_status="processing",
            updated_at=timezone.now()
        )

        # Запускаем задачу
        try:
            process_video_async.delay(video.id, None)
            started += 1
            logger.info(f"Started processing video {video.id}")
        except Exception as e:
            Video.objects.filter(pk=video.pk).update(
                processing_status="pending",
                processing_error=f"Enqueue error: {e}"
            )
            skipped += 1
            logger.error(f"Failed to enqueue video {video.id}: {e}")

    if started > 0 or reset > 0:
        logger.info(f"process_pending_videos: started={started}, skipped={skipped}, reset={reset}")


@shared_task
def check_alert_rules():
    """Check all active alert rules and trigger alerts if needed."""
    from .services.alert_service import AlertService
    
    service = AlertService()
    alerts_triggered = service.check_all_rules()
    
    print(f"[ALERTS] Checked alert rules, triggered {alerts_triggered} alerts")
    return alerts_triggered
