"""
Rating views for video voting system.
"""
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from .models import Rating, Video


def get_rating_stats(video):
    """
    Get rating statistics for a video.

    Returns:
        dict: {
            'likes': int,
            'dislikes': int,
            'total': int,
            'likes_percent': float,
            'dislikes_percent': float,
            'emoji': str
        }
    """
    likes = Rating.objects.filter(video=video, value=1).count()
    dislikes = Rating.objects.filter(video=video, value=-1).count()
    total = likes + dislikes

    if total == 0:
        likes_percent = 0
        dislikes_percent = 0
        emoji = "😐"
    else:
        likes_percent = round((likes / total) * 100, 1)
        dislikes_percent = round((dislikes / total) * 100, 1)

        # Определяем смайлик
        if likes_percent >= 70:
            emoji = "😊"
        elif likes_percent >= 30:
            emoji = "😐"
        else:
            emoji = "😞"

    return {
        "likes": likes,
        "dislikes": dislikes,
        "total": total,
        "likes_percent": likes_percent,
        "dislikes_percent": dislikes_percent,
        "emoji": emoji,
    }


def get_user_rating(video, user, ip_address):
    """
    Get user's rating for a video.

    Returns:
        int: 1 for like, -1 for dislike, 0 for no rating, None if not found
    """
    if user and user.is_authenticated:
        try:
            rating = Rating.objects.get(video=video, user=user)
            return rating.value
        except Rating.DoesNotExist:
            return 0
    elif ip_address:
        try:
            rating = Rating.objects.get(
                video=video, ip_address=ip_address, user__isnull=True
            )
            return rating.value
        except Rating.DoesNotExist:
            return 0
    return 0


@require_http_methods(["POST"])
def video_rating(request, slug):
    """Handle video rating (like/dislike) via HTMX."""
    video = get_object_or_404(Video, slug=slug, status="published")
    value = int(request.POST.get("value", 1))

    # Get user and IP
    user = request.user if request.user.is_authenticated else None
    ip_address = request.META.get("REMOTE_ADDR")

    # Check if user already rated
    existing_rating = None
    if user:
        try:
            existing_rating = Rating.objects.get(video=video, user=user)
        except Rating.DoesNotExist:
            pass
    elif ip_address:
        try:
            existing_rating = Rating.objects.get(
                video=video, ip_address=ip_address, user__isnull=True
            )
        except Rating.DoesNotExist:
            pass

    # Handle rating
    if existing_rating:
        if existing_rating.value == value:
            # Remove rating if clicking the same button
            existing_rating.delete()
        else:
            # Change rating
            existing_rating.value = value
            existing_rating.save()
    else:
        # Create new rating
        try:
            Rating.objects.create(
                video=video,
                user=user if user and user.is_authenticated else None,
                ip_address=ip_address if not (user and user.is_authenticated) else None,
                value=value,
            )
        except ValueError as e:
            # Rating already exists (race condition)
            return JsonResponse({"error": str(e)}, status=400)

    # Get updated stats
    stats = get_rating_stats(video)
    user_rating = get_user_rating(video, user, ip_address)

    return render(
        request,
        "videos/htmx/rating_widget.html",
        {"video": video, "stats": stats, "user_rating": user_rating},
    )


@require_http_methods(["GET"])
def video_rating_widget(request, slug):
    """Get rating widget for video."""
    video = get_object_or_404(Video, slug=slug, status="published")

    user = request.user if request.user.is_authenticated else None
    ip_address = request.META.get("REMOTE_ADDR")

    stats = get_rating_stats(video)
    user_rating = get_user_rating(video, user, ip_address)

    return render(
        request,
        "videos/htmx/rating_widget.html",
        {"video": video, "stats": stats, "user_rating": user_rating},
    )
