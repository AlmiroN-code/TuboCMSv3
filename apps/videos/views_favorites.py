"""
Views for favorites and playlists functionality.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import Video
from .models_favorites import (
    Favorite,
    Playlist,
    PlaylistFollow,
    PlaylistLike,
    PlaylistVideo,
)


@login_required
@require_http_methods(["POST"])
def add_to_favorites(request, video_id):
    """Add video to user's favorites."""
    video = get_object_or_404(Video, id=video_id, status="published")

    favorite, created = Favorite.objects.get_or_create(user=request.user, video=video)

    if created:
        return JsonResponse(
            {
                "success": True,
                "message": "Видео добавлено в избранное",
                "action": "added",
            }
        )
    else:
        return JsonResponse({"success": False, "error": "Видео уже в избранном"})


@login_required
@require_http_methods(["POST"])
def remove_from_favorites(request, video_id):
    """Remove video from user's favorites."""
    video = get_object_or_404(Video, id=video_id)

    try:
        favorite = Favorite.objects.get(user=request.user, video=video)
        favorite.delete()
        return JsonResponse(
            {
                "success": True,
                "message": "Видео удалено из избранного",
                "action": "removed",
            }
        )
    except Favorite.DoesNotExist:
        return JsonResponse({"success": False, "error": "Видео не найдено в избранном"})


@login_required
def favorites_list(request):
    """Display user's favorite videos."""
    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related("video__created_by", "video__category")
        .prefetch_related("video__tags")
        .order_by("-created_at")
    )

    # Pagination
    paginator = Paginator(favorites, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "favorites": page_obj,
        "total_count": paginator.count,
    }
    return render(request, "videos/favorites.html", context)


@login_required
def playlists_list(request):
    """Display user's playlists."""
    playlists = (
        Playlist.objects.filter(user=request.user)
        .annotate(videos_count=Count("playlist_videos"), likes_count=Count("likes"))
        .order_by("-created_at")
    )

    context = {
        "playlists": playlists,
    }
    return render(request, "videos/playlists.html", context)


@login_required
def playlist_create(request):
    """Create a new playlist."""
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        privacy = request.POST.get("privacy", "public")

        if not title:
            messages.error(request, "Название плейлиста обязательно")
            return render(request, "videos/playlist_create.html")

        playlist = Playlist.objects.create(
            user=request.user, title=title, description=description, privacy=privacy
        )

        messages.success(request, "Плейлист создан успешно")
        return redirect("videos:playlist_detail", playlist_id=playlist.id)

    return render(request, "videos/playlist_create.html")


def playlist_detail(request, playlist_id):
    """Display playlist details."""
    playlist = get_object_or_404(Playlist, id=playlist_id)

    # Check privacy permissions
    if playlist.privacy == "private" and playlist.user != request.user:
        messages.error(request, "Плейлист недоступен")
        return redirect("videos:playlists_list")

    # Get playlist videos
    playlist_videos = (
        PlaylistVideo.objects.filter(playlist=playlist)
        .select_related("video__created_by", "video__category")
        .prefetch_related("video__tags")
        .order_by("order", "created_at")
    )

    # Check if user follows this playlist
    is_following = False
    if request.user.is_authenticated and playlist.user != request.user:
        is_following = PlaylistFollow.objects.filter(
            user=request.user, playlist=playlist
        ).exists()

    # Check if user liked this playlist
    is_liked = False
    if request.user.is_authenticated:
        is_liked = PlaylistLike.objects.filter(
            user=request.user, playlist=playlist
        ).exists()

    context = {
        "playlist": playlist,
        "playlist_videos": playlist_videos,
        "is_following": is_following,
        "is_liked": is_liked,
        "can_edit": request.user == playlist.user,
    }
    return render(request, "videos/playlist_detail.html", context)


@login_required
def playlist_edit(request, playlist_id):
    """Edit playlist."""
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        privacy = request.POST.get("privacy", "public")

        if not title:
            messages.error(request, "Название плейлиста обязательно")
        else:
            playlist.title = title
            playlist.description = description
            playlist.privacy = privacy
            playlist.save()

            messages.success(request, "Плейлист обновлен")
            return redirect("videos:playlist_detail", playlist_id=playlist.id)

    context = {
        "playlist": playlist,
    }
    return render(request, "videos/playlist_edit.html", context)


@login_required
@require_http_methods(["POST"])
def playlist_delete(request, playlist_id):
    """Delete playlist."""
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    playlist.delete()

    messages.success(request, "Плейлист удален")
    return redirect("videos:playlists_list")


@login_required
@require_http_methods(["POST"])
def add_to_playlist(request, video_id):
    """Add video to playlist."""
    video = get_object_or_404(Video, id=video_id, status="published")
    playlist_id = request.POST.get("playlist_id")

    if not playlist_id:
        return JsonResponse({"success": False, "error": "Плейлист не выбран"})

    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)

    # Check if video is already in playlist
    if PlaylistVideo.objects.filter(playlist=playlist, video=video).exists():
        return JsonResponse({"success": False, "error": "Видео уже в плейлисте"})

    # Add video to playlist
    PlaylistVideo.objects.create(playlist=playlist, video=video)

    return JsonResponse(
        {"success": True, "message": f'Видео добавлено в плейлист "{playlist.title}"'}
    )


@login_required
@require_http_methods(["POST"])
def remove_from_playlist(request, playlist_id, video_id):
    """Remove video from playlist."""
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    video = get_object_or_404(Video, id=video_id)

    try:
        playlist_video = PlaylistVideo.objects.get(playlist=playlist, video=video)
        playlist_video.delete()

        messages.success(request, "Видео удалено из плейлиста")
    except PlaylistVideo.DoesNotExist:
        messages.error(request, "Видео не найдено в плейлисте")

    return redirect("videos:playlist_detail", playlist_id=playlist.id)


@login_required
@require_http_methods(["POST"])
def playlist_like(request, playlist_id):
    """Like/unlike playlist."""
    playlist = get_object_or_404(Playlist, id=playlist_id)

    like, created = PlaylistLike.objects.get_or_create(
        user=request.user, playlist=playlist
    )

    if created:
        return JsonResponse(
            {
                "success": True,
                "message": "Плейлист добавлен в понравившиеся",
                "action": "liked",
            }
        )
    else:
        like.delete()
        return JsonResponse(
            {
                "success": True,
                "message": "Плейлист удален из понравившихся",
                "action": "unliked",
            }
        )


@login_required
@require_http_methods(["POST"])
def playlist_follow(request, playlist_id):
    """Follow/unfollow playlist."""
    playlist = get_object_or_404(Playlist, id=playlist_id)

    if playlist.user == request.user:
        return JsonResponse(
            {"success": False, "error": "Нельзя подписаться на свой плейлист"}
        )

    follow, created = PlaylistFollow.objects.get_or_create(
        user=request.user, playlist=playlist
    )

    if created:
        return JsonResponse(
            {
                "success": True,
                "message": "Вы подписались на плейлист",
                "action": "followed",
            }
        )
    else:
        follow.delete()
        return JsonResponse(
            {
                "success": True,
                "message": "Вы отписались от плейлиста",
                "action": "unfollowed",
            }
        )


def public_playlists(request):
    """Display public playlists."""
    playlists = (
        Playlist.objects.filter(privacy="public")
        .select_related("user")
        .annotate(
            videos_count=Count("playlist_videos"),
            likes_count=Count("likes"),
            followers_count=Count("followers"),
        )
        .order_by("-created_at")
    )

    # Search and filtering
    search = request.GET.get("search", "").strip()
    if search:
        playlists = playlists.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(user__username__icontains=search)
        )

    # Sorting
    sort = request.GET.get("sort", "newest")
    if sort == "popular":
        playlists = playlists.order_by("-likes_count", "-created_at")
    elif sort == "most_videos":
        playlists = playlists.order_by("-videos_count", "-created_at")
    elif sort == "most_followed":
        playlists = playlists.order_by("-followers_count", "-created_at")
    else:  # newest
        playlists = playlists.order_by("-created_at")

    # Pagination
    paginator = Paginator(playlists, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "playlists": page_obj,
        "search": search,
        "sort": sort,
    }
    return render(request, "videos/public_playlists_simple.html", context)


@login_required
def user_playlists_modal(request, video_id):
    """HTMX modal for adding video to playlists."""
    video = get_object_or_404(Video, id=video_id, status="published")

    # Get user's playlists
    playlists = (
        Playlist.objects.filter(user=request.user)
        .annotate(
            videos_count=Count("playlist_videos"),
            has_video=Count("playlist_videos", filter=Q(playlist_videos__video=video)),
        )
        .order_by("-created_at")
    )

    context = {
        "video": video,
        "playlists": playlists,
    }
    return render(request, "videos/htmx/playlists_modal.html", context)


@login_required
@require_http_methods(["POST"])
def add_to_playlist(request, video_id):
    """Add video to playlist."""
    video = get_object_or_404(Video, id=video_id, status="published")
    playlist_id = request.POST.get("playlist_id")

    if not playlist_id:
        return JsonResponse({"error": "Playlist ID required"}, status=400)

    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)

    # Check if video is already in playlist
    if PlaylistVideo.objects.filter(playlist=playlist, video=video).exists():
        return JsonResponse({"error": "Video already in playlist"}, status=400)

    # Add video to playlist
    PlaylistVideo.objects.create(
        playlist=playlist, video=video, order=playlist.playlist_videos.count() + 1
    )

    return JsonResponse(
        {"success": True, "message": f'Видео добавлено в плейлист "{playlist.title}"'}
    )


@login_required
@require_http_methods(["POST"])
def remove_from_playlist(request, playlist_id, video_id):
    """Remove video from playlist."""
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    video = get_object_or_404(Video, id=video_id)

    playlist_video = get_object_or_404(PlaylistVideo, playlist=playlist, video=video)
    playlist_video.delete()

    messages.success(request, "Видео удалено из плейлиста")
    return redirect("videos:playlist_detail", playlist_id=playlist.id)
