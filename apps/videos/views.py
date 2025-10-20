"""
Video views for TubeCMS.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Video, VideoLike, VideoView, VideoReport
from .forms import VideoUploadForm, VideoEditForm, VideoSearchForm, VideoReportForm
from .services import VideoViewService, VideoLikeService, VideoSearchService
from apps.core.models import Category


def video_list(request):
    """List all videos."""
    videos = Video.objects.filter(is_published=True, status='published').select_related('user', 'category').prefetch_related('tags')
    
    # Search
    search_form = VideoSearchForm(request.GET)
    if search_form.is_valid():
        query = search_form.cleaned_data.get('query')
        category = search_form.cleaned_data.get('category')
        sort = search_form.cleaned_data.get('sort', 'newest')
        
        if query:
            videos = videos.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct()
        
        if category:
            videos = videos.filter(category__slug=category)
        
        # Sorting
        if sort == 'popular':
            videos = videos.order_by('-views_count', '-created_at')
        elif sort == 'oldest':
            videos = videos.order_by('created_at')
        elif sort == 'trending':
            from django.utils import timezone
            from datetime import timedelta
            week_ago = timezone.now() - timedelta(days=7)
            videos = videos.filter(created_at__gte=week_ago).order_by('-views_count')
        else:  # newest
            videos = videos.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(videos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'videos': page_obj,
        'search_form': search_form,
    }
    return render(request, 'videos/list.html', context)


def video_detail(request, slug):
    """Video detail page."""
    video = get_object_or_404(
        Video.objects.select_related('user', 'category').prefetch_related('tags'),
        slug=slug,
        is_published=True
    )
    
    # Track view
    VideoViewService.track_view(video, request)
    
    # Get related videos
    related_videos = Video.objects.filter(is_published=True, status='published').filter(
        category=video.category
    ).exclude(id=video.id).select_related('user', 'category')[:6]
    
    # Get user's like status
    user_like = None
    if request.user.is_authenticated:
        try:
            like = VideoLike.objects.get(video=video, user=request.user)
            user_like = like.value
        except VideoLike.DoesNotExist:
            user_like = 0
    
    # Get comments
    from apps.comments.models import Comment
    comments = Comment.objects.filter(video=video, parent=None).select_related('user').order_by('-created_at')
    
    context = {
        'video': video,
        'related_videos': related_videos,
        'user_like': user_like,
        'comments': comments,
    }
    return render(request, 'videos/detail.html', context)


@login_required
def video_upload(request):
    """Upload new video."""
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.user = request.user
            video.save()
            form.save_m2m()  # Save many-to-many relationships
            
            messages.success(request, 'Видео загружено! Обработка начнется в ближайшее время.')
            return redirect('videos:detail', slug=video.slug)
    else:
        form = VideoUploadForm()
    
    return render(request, 'videos/upload.html', {'form': form})


@login_required
def video_edit(request, slug):
    """Edit video."""
    video = get_object_or_404(Video, slug=slug, user=request.user)
    
    if request.method == 'POST':
        form = VideoEditForm(request.POST, request.FILES, instance=video)
        if form.is_valid():
            form.save()
            messages.success(request, 'Видео обновлено!')
            return redirect('videos:detail', slug=video.slug)
    else:
        form = VideoEditForm(instance=video)
    
    return render(request, 'videos/edit.html', {'form': form, 'video': video})


@login_required
def video_delete(request, slug):
    """Delete video."""
    video = get_object_or_404(Video, slug=slug, user=request.user)
    
    if request.method == 'POST':
        video.delete()
        messages.success(request, 'Видео удалено!')
        return redirect('users:profile', username=request.user.username)
    
    return render(request, 'videos/delete_confirm.html', {'video': video})


@login_required
@require_http_methods(["POST"])
def video_like(request, slug):
    """Like/dislike video."""
    video = get_object_or_404(Video, slug=slug)
    value = int(request.POST.get('value', 1))
    
    result = VideoLikeService.toggle_like(video, request.user, value)
    
    if result:
        return JsonResponse(result)
    else:
        return JsonResponse({'error': 'Failed to update like'}, status=400)


@require_http_methods(["POST"])
def video_report(request, slug):
    """Report video."""
    video = get_object_or_404(Video, slug=slug)
    
    if request.method == 'POST':
        form = VideoReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.video = video
            report.user = request.user if request.user.is_authenticated else None
            report.save()
            
            messages.success(request, 'Жалоба отправлена. Спасибо за обратную связь!')
            return redirect('videos:detail', slug=video.slug)
    else:
        form = VideoReportForm()
    
    return render(request, 'videos/report.html', {'form': form, 'video': video})


def category_videos(request, slug):
    """Videos by category."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    videos = Video.objects.filter(category=category, is_published=True, status='published').select_related('user', 'category')
    
    # Pagination
    paginator = Paginator(videos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'videos': page_obj,
    }
    return render(request, 'videos/category.html', context)


@login_required
def my_videos(request):
    """User's videos."""
    videos = Video.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(videos, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'videos': page_obj,
    }
    return render(request, 'videos/my_videos.html', context)
