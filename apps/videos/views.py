"""
Video views for TubeCMS.
"""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.core.models import Category

from .forms import VideoEditForm, VideoReportForm, VideoSearchForm, VideoUploadForm
from .models import Video, VideoLike, VideoReport, VideoView, WatchLater
from .services_legacy import VideoSearchService, VideoViewService


def video_list(request):
    """List all videos."""
    videos = (
        Video.objects.filter(status="published")
        .select_related("created_by", "category")
        .prefetch_related("tags", "ratings", "encoded_files__profile")
    )

    # Search
    search_form = VideoSearchForm(request.GET)
    if search_form.is_valid():
        query = search_form.cleaned_data.get("query")
        category = search_form.cleaned_data.get("category")
        sort = search_form.cleaned_data.get("sort", "newest")

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
        elif sort == "trending":
            from datetime import timedelta

            from django.utils import timezone

            week_ago = timezone.now() - timedelta(days=7)
            videos = videos.filter(created_at__gte=week_ago).order_by("-views_count")
        else:  # newest
            videos = videos.order_by("-created_at")

    # Pagination
    paginator = Paginator(videos, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "videos": page_obj,
        "search_form": search_form,
    }
    return render(request, "videos/list.html", context)


def video_detail(request, slug):
    """Video detail page."""
    from .constants import RELATED_VIDEOS_LIMIT

    video = get_object_or_404(
        Video.objects.select_related("created_by", "category").prefetch_related("tags"),
        slug=slug,
        status="published",
    )

    # Track view
    VideoViewService.track_view(video, request)

    # Get related videos
    related_videos = (
        Video.objects.filter(status="published", category=video.category)
        .exclude(id=video.id)
        .select_related("created_by", "category")
        .prefetch_related("tags")[:RELATED_VIDEOS_LIMIT]
    )

    # Get comments with prefetch for likes
    from apps.comments.models import Comment

    comments = (
        Comment.objects.filter(video=video, parent=None)
        .select_related("user")
        .prefetch_related("replies__user", "likes")
        .order_by("-created_at")
    )

    # Get rating stats and user rating
    from .rating_views import get_rating_stats, get_user_rating

    rating_stats = get_rating_stats(video)
    user_rating = get_user_rating(video, request.user, request.META.get("REMOTE_ADDR"))

    # Check if video is in user's favorites and watch later
    is_favorite = False
    is_watch_later = False
    if request.user.is_authenticated:
        from .models_favorites import Favorite

        is_favorite = Favorite.objects.filter(user=request.user, video=video).exists()
        is_watch_later = WatchLater.objects.filter(
            user=request.user, video=video
        ).exists()

    # Check if video has ready streams
    has_streams = video.streams.filter(is_ready=True).exists()
    has_hls = video.streams.filter(stream_type='hls', is_ready=True).exists()
    has_dash = video.streams.filter(stream_type='dash', is_ready=True).exists()

    context = {
        "video": video,
        "related_videos": related_videos,
        "comments": comments,
        "rating_stats": rating_stats,
        "user_rating": user_rating,
        "is_favorite": is_favorite,
        "is_watch_later": is_watch_later,
        "has_streams": has_streams,
        "has_hls": has_hls,
        "has_dash": has_dash,
    }
    return render(request, "videos/detail.html", context)


@login_required
def video_upload(request):
    """Upload new video."""
    from apps.core.utils import get_site_settings

    site_settings = get_site_settings()

    # Проверяем, разрешена ли регистрация
    if site_settings and not site_settings.allow_registration:
        messages.error(request, "Регистрация новых пользователей временно отключена.")
        return redirect("core:home")

    if request.method == "POST":
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.created_by = request.user  # Автор - тот кто публикует
            # Ensure uploaded file from form is stored into model field used by processing
            uploaded_file = form.cleaned_data.get("video_file")
            if uploaded_file:
                video.temp_video_file = uploaded_file

            # Применяем настройки автоматической публикации
            if site_settings and site_settings.auto_publish_videos:
                video.status = "published"
            else:
                video.status = "draft"

            video.save()

            # Обрабатываем теги из tags_input
            tags_input = form.cleaned_data.get("tags_input", [])
            if tags_input:
                video.tags.set(tags_input)
            else:
                form.save_m2m()  # Используем стандартное сохранение, если tags_input не используется

            # Обрабатываем модели (performers)
            performers = form.cleaned_data.get("performers", [])
            if performers:
                from apps.models.models import ModelVideo

                # Очищаем существующие связи
                video.performers.clear()
                # Создаем новые связи
                for i, performer in enumerate(performers):
                    ModelVideo.objects.create(
                        video=video,
                        model=performer,
                        is_primary=(i == 0),  # Первая модель - основная
                    )

            messages.success(
                request, "Видео загружено! Обработка начнется в ближайшее время."
            )
            return redirect("videos:detail", slug=video.slug)
    else:
        form = VideoUploadForm()

    return render(
        request, "videos/upload.html", {"form": form, "site_settings": site_settings}
    )


@login_required
def video_edit(request, slug):
    """Edit video."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category").prefetch_related(
            "tags", "performers"
        ),
        slug=slug,
        created_by=request.user,
    )

    if request.method == "POST":
        form = VideoEditForm(request.POST, request.FILES, instance=video)
        if form.is_valid():
            video = form.save(commit=False)
            video.save()

            # Обрабатываем теги из tags_input
            tags_input = form.cleaned_data.get("tags_input", [])
            if tags_input:
                video.tags.set(tags_input)
            else:
                form.save_m2m()

            # Обрабатываем модели (performers)
            performers = form.cleaned_data.get("performers", [])
            if performers is not None:  # Проверяем, что поле было в форме
                from apps.models.models import ModelVideo

                # Очищаем существующие связи
                video.performers.clear()
                # Создаем новые связи
                for i, performer in enumerate(performers):
                    ModelVideo.objects.create(
                        video=video,
                        model=performer,
                        is_primary=(i == 0),  # Первая модель - основная
                    )

            messages.success(request, "Видео обновлено!")
            return redirect("videos:detail", slug=video.slug)
    else:
        form = VideoEditForm(instance=video)

    return render(request, "videos/edit.html", {"form": form, "video": video})


@login_required
def video_delete(request, slug):
    """Delete video."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"),
        slug=slug,
        created_by=request.user,
    )

    if request.method == "POST":
        video.delete()
        messages.success(request, "Видео удалено!")
        return redirect("members:profile", username=request.user.username)

    return render(request, "videos/delete_confirm.html", {"video": video})


@login_required
@require_http_methods(["POST"])
def video_like(request, slug):
    """Like/dislike video."""
    from django.db.models import Count, Q

    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=slug
    )
    value = int(request.POST.get("value", 1))

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

        # Get updated counts using annotations
        video_with_counts = (
            Video.objects.filter(pk=video.pk)
            .annotate(
                likes_count=Count("likes", filter=Q(likes__value=1)),
                dislikes_count=Count("likes", filter=Q(likes__value=-1)),
            )
            .first()
        )

        return JsonResponse(
            {
                "likes_count": video_with_counts.likes_count
                if video_with_counts
                else 0,
                "dislikes_count": video_with_counts.dislikes_count
                if video_with_counts
                else 0,
            }
        )
    except Exception as e:
        return JsonResponse({"error": "Failed to update like"}, status=400)


@require_http_methods(["POST"])
def video_report(request, slug):
    """Report video."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=slug
    )

    if request.method == "POST":
        form = VideoReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.video = video
            report.user = request.user if request.user.is_authenticated else None
            report.save()

            messages.success(request, "Жалоба отправлена. Спасибо за обратную связь!")
            return redirect("videos:detail", slug=video.slug)
    else:
        form = VideoReportForm()

    return render(request, "videos/report.html", {"form": form, "video": video})


def category_videos(request, slug):
    """Videos by category."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    videos = (
        Video.objects.filter(category=category, status="published")
        .select_related("created_by", "category")
        .prefetch_related("tags")
    )

    # Pagination
    paginator = Paginator(videos, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "category": category,
        "videos": page_obj,
    }
    return render(request, "videos/category.html", context)


@login_required
def my_videos(request):
    """User's videos."""
    videos = (
        Video.objects.filter(created_by=request.user)
        .select_related("created_by", "category")
        .prefetch_related("tags")
        .order_by("-created_at")
    )

    # Pagination
    paginator = Paginator(videos, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "videos": page_obj,
    }
    return render(request, "videos/my_videos.html", context)


@login_required
def watch_later_list(request, username=None):
    """Страница «Watch Later» для конкретного пользователя."""
    from apps.users.models import User

    # Если username передан (новый URL), используем его, иначе текущего пользователя (старый URL)
    if username:
        profile_user = get_object_or_404(
            User.objects.select_related("profile"), username=username
        )
        # Проверяем права доступа - только сам пользователь может видеть свой Watch Later
        if request.user != profile_user:
            messages.error(request, "У вас нет доступа к этому списку.")
            return redirect("members:profile", username=username)
        target_user = profile_user
    else:
        target_user = request.user

    # Используем prefetch_related для оптимизации
    watch_later_qs = (
        WatchLater.objects.filter(user=target_user)
        .select_related("video", "video__created_by", "video__category")
        .prefetch_related("video__tags")
        .order_by("-created_at")
    )

    # Пагинация на уровне QuerySet
    paginator = Paginator(watch_later_qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Извлекаем видео из page_obj
    videos = [wl.video for wl in page_obj]

    context = {
        "videos": videos,
        "page_obj": page_obj,  # Для пагинации в шаблоне
        "profile_user": target_user,
    }
    return render(request, "videos/watch_later.html", context)


# Import favorites and playlists views
from .views_favorites import (
    add_to_favorites,
    add_to_playlist,
    favorites_list,
    playlist_create,
    playlist_delete,
    playlist_detail,
    playlist_edit,
    playlist_follow,
    playlist_like,
    playlists_list,
    public_playlists,
    remove_from_favorites,
    remove_from_playlist,
    user_playlists_modal,
)
