"""
Views for video processing progress tracking.
"""
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .models import Video

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def video_processing_progress(request, video_id):
    """
    Get video processing progress.
    
    Returns JSON with:
    - progress: 0-100 percentage
    - status: current processing status
    - processing_status: pending/processing/completed/failed/error
    - error_message: if any error occurred
    """
    video = get_object_or_404(Video, id=video_id, created_by=request.user)
    
    # Determine status message based on processing_status
    status_messages = {
        "pending": "Waiting in queue...",
        "processing": "Processing video...",
        "completed": "Processing completed!",
        "failed": "Processing failed",
        "error": "An error occurred",
    }
    
    status_message = status_messages.get(
        video.processing_status, 
        "Unknown status"
    )
    
    # If there's a specific error, use it
    if video.processing_error:
        status_message = video.processing_error[:100]  # Limit length
    
    response_data = {
        "progress": video.processing_progress,
        "status": status_message,
        "processing_status": video.processing_status,
        "video_status": video.status,
        "error_message": video.processing_error if video.processing_error else None,
        "is_completed": video.processing_status == "completed",
        "is_failed": video.processing_status in ["failed", "error"],
    }
    
    return JsonResponse(response_data)


@login_required
@require_http_methods(["POST"])
def retry_video_processing(request, video_id):
    """
    Retry failed video processing.
    """
    video = get_object_or_404(Video, id=video_id, created_by=request.user)
    
    # Only allow retry for failed/error videos
    if video.processing_status not in ["failed", "error"]:
        return JsonResponse({
            "success": False,
            "error": "Video is not in failed state"
        }, status=400)
    
    # Check if temp file still exists
    if not video.temp_video_file:
        return JsonResponse({
            "success": False,
            "error": "Original video file not found"
        }, status=400)
    
    try:
        # Reset processing status
        video.processing_status = "pending"
        video.processing_progress = 0
        video.processing_error = ""
        video.save(update_fields=[
            "processing_status", 
            "processing_progress", 
            "processing_error"
        ])
        
        # Import here to avoid circular imports
        from .tasks import process_video_async
        
        # Queue for processing
        process_video_async.delay(video.id)
        
        logger.info(f"Retrying video processing for video {video.id}")
        
        return JsonResponse({
            "success": True,
            "message": "Video queued for reprocessing"
        })
        
    except Exception as e:
        logger.error(f"Error retrying video processing: {e}", exc_info=True)
        return JsonResponse({
            "success": False,
            "error": "Failed to queue video for processing"
        }, status=500)