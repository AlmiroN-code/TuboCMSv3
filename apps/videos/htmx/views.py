"""
HTMX-specific views for videos.
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q

from ..models import Video, VideoLike
from ..services import VideoLikeService


@require_http_methods(["GET"])
def video_list_partial(request):
    """HTMX partial for video list."""
    videos = Video.objects.filter(is_published=True, status='published').select_related('user', 'category').prefetch_related('tags')
    
    # Search and filters
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    sort = request.GET.get('sort', 'newest')
    
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
    else:  # newest
        videos = videos.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(videos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'videos/htmx/list_partial.html', {'videos': page_obj})


@require_http_methods(["POST"])
def video_like_htmx(request, slug):
    """HTMX like/dislike video."""
    video = get_object_or_404(Video, slug=slug)
    value = int(request.POST.get('value', 1))
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    result = VideoLikeService.toggle_like(video, request.user, value)
    
    if result:
        # Refresh video from database to get updated counts
        video.refresh_from_db()
        
        # Get user's current like status
        user_like = 0
        try:
            like = VideoLike.objects.get(video=video, user=request.user)
            user_like = like.value
        except VideoLike.DoesNotExist:
            user_like = 0
        
        return render(request, 'videos/htmx/like_buttons.html', {
            'video': video,
            'user_like': user_like
        })
    else:
        return JsonResponse({'error': 'Failed to update like'}, status=400)


@require_http_methods(["GET"])
def video_actions(request, slug):
    """HTMX video actions (like, share, etc.)."""
    video = get_object_or_404(Video, slug=slug)
    
    # Get user's like status
    user_like = None
    if request.user.is_authenticated:
        try:
            like = VideoLike.objects.get(video=video, user=request.user)
            user_like = like.value
        except VideoLike.DoesNotExist:
            user_like = 0
    
    return render(request, 'videos/htmx/actions.html', {
        'video': video,
        'user_like': user_like
    })


@require_http_methods(["GET"])
def video_progress(request, slug):
    """HTMX video processing progress."""
    video = get_object_or_404(Video, slug=slug)
    
    return render(request, 'videos/htmx/progress.html', {'video': video})


@require_http_methods(["GET"])
def video_recommendations(request, slug):
    """HTMX video recommendations."""
    video = get_object_or_404(Video, slug=slug)
    
    # Get related videos
    related_videos = Video.objects.filter(is_published=True, status='published').filter(
        category=video.category
    ).exclude(id=video.id).select_related('user', 'category')[:6]
    
    return render(request, 'videos/htmx/recommendations.html', {
        'videos': related_videos
    })


@require_http_methods(["GET"])
def video_search_suggestions(request):
    """HTMX search suggestions."""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    # Get video titles that match query
    videos = Video.objects.filter(is_published=True, status='published').filter(
        title__icontains=query
    ).values_list('title', flat=True)[:5]
    
    suggestions = list(videos)
    
    return JsonResponse({'suggestions': suggestions})


@require_http_methods(["GET"])
def video_upload_progress(request, video_id):
    """HTMX upload progress."""
    video = get_object_or_404(Video, id=video_id, user=request.user)
    
    return render(request, 'videos/htmx/upload_progress.html', {'video': video})
