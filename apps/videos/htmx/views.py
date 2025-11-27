"""
HTMX-specific views for videos.
"""

from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from apps.videos.models_favorites import Favorite

from ..constants import (
    RECOMMENDATIONS_CACHE_TIMEOUT,
    RELATED_VIDEOS_LIMIT,
    VIDEOS_PER_PAGE,
)
from ..models import Video, VideoLike, WatchLater


@require_http_methods(["GET"])
def video_list_partial(request):
    """HTMX partial for video list."""
    videos = (
        Video.objects.filter(status="published")
        .select_related("created_by", "category")
        .prefetch_related("tags")
    )

    # Search and filters
    query = request.GET.get("q", "")
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "newest")

    if query:
        videos = videos.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()

    if category:
        videos = videos.filter(category__slug=category)

    # Sorting
    if sort == "popular":
        videos = videos.order_by("-views_count", "-created_at")
    elif sort == "oldest":
        videos = videos.order_by("created_at")
    else:  # newest
        videos = videos.order_by("-created_at")

    # Pagination
    paginator = Paginator(videos, VIDEOS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "videos/htmx/list_partial.html", {"videos": page_obj})


@require_http_methods(["POST"])
def video_like_htmx(request, slug):
    """HTMX like/dislike video."""
    from django.db.models import Count, Q

    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=slug
    )
    value = int(request.POST.get("value", 1))

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    try:
        like, created = VideoLike.objects.get_or_create(
            video=video, user=request.user, defaults={"value": value}
        )

        if not created:
            if like.value == value:
                # Remove like/dislike
                like.delete()
            else:
                # Change like/dislike
                like.value = value
                like.save()

        # Get updated video with counts using annotations
        video = (
            Video.objects.filter(pk=video.pk)
            .annotate(
                likes_count=Count("likes", filter=Q(likes__value=1)),
                dislikes_count=Count("likes", filter=Q(likes__value=-1)),
            )
            .select_related("created_by", "category")
            .prefetch_related("tags")
            .first()
        )

        return render(request, "videos/htmx/like_buttons.html", {"video": video})
    except Exception as e:
        return JsonResponse({"error": "Failed to update like"}, status=400)


@require_http_methods(["GET"])
def video_actions(request, slug):
    """HTMX video actions (like, share, etc.)."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category").prefetch_related("tags"),
        slug=slug,
    )

    return render(request, "videos/htmx/actions.html", {"video": video})


@require_http_methods(["GET"])
def video_progress(request, slug):
    """HTMX video processing progress."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=slug
    )

    return render(request, "videos/htmx/progress.html", {"video": video})


@cache_page(RECOMMENDATIONS_CACHE_TIMEOUT)
@require_http_methods(["GET"])
def video_recommendations(request, slug):
    """HTMX video recommendations."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=slug
    )

    # Get related videos
    related_videos = (
        Video.objects.filter(status="published")
        .filter(category=video.category)
        .exclude(id=video.id)
        .select_related("created_by", "category")
        .prefetch_related("tags")[:RELATED_VIDEOS_LIMIT]
    )

    return render(
        request, "videos/htmx/recommendations.html", {"videos": related_videos}
    )


@require_http_methods(["GET"])
def video_upload_progress(request, video_id):
    """HTMX upload progress."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"),
        id=video_id,
        created_by=request.user,
    )

    return render(request, "videos/htmx/upload_progress.html", {"video": video})


@require_http_methods(["POST"])
def watch_later_toggle(request, slug):
    """HTMX: добавить/убрать видео в Watch Later и вернуть кнопку."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=slug
    )
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    existed = WatchLater.objects.filter(user=request.user, video=video).exists()
    if existed:
        WatchLater.objects.filter(user=request.user, video=video).delete()
        active = False
    else:
        WatchLater.objects.create(user=request.user, video=video)
        active = True

    return render(
        request,
        "videos/htmx/watch_later_button.html",
        {
            "video": video,
            "active": active,
        },
    )


@require_http_methods(["GET"])
def watch_later_button(request, slug):
    """HTMX: отрендерить кнопку Watch Later с текущим состоянием."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=slug
    )
    active = False
    if request.user.is_authenticated:
        active = WatchLater.objects.filter(user=request.user, video=video).exists()
    return render(
        request,
        "videos/htmx/watch_later_button.html",
        {
            "video": video,
            "active": active,
        },
    )


@require_http_methods(["POST"])
def favorite_toggle(request, slug):
    """HTMX: добавить/убрать видео в избранное и вернуть кнопку."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=slug
    )
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    existed = Favorite.objects.filter(user=request.user, video=video).exists()
    if existed:
        Favorite.objects.filter(user=request.user, video=video).delete()
        active = False
    else:
        Favorite.objects.create(user=request.user, video=video)
        active = True

    return render(
        request,
        "videos/htmx/favorite_button.html",
        {
            "video": video,
            "active": active,
        },
    )


@require_http_methods(["GET"])
def favorite_button(request, slug):
    """HTMX: отрендерить кнопку Favorite с текущим состоянием."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=slug
    )
    active = False
    if request.user.is_authenticated:
        active = Favorite.objects.filter(user=request.user, video=video).exists()
    return render(
        request,
        "videos/htmx/favorite_button.html",
        {
            "video": video,
            "active": active,
        },
    )


@require_http_methods(["GET"])
def playlist_button(request, slug):
    """HTMX: отрендерить кнопку Add to Playlist."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=slug
    )
    return render(
        request,
        "videos/htmx/playlist_button.html",
        {
            "video": video,
        },
    )
