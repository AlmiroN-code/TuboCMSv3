"""
Core views for TubeCMS.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Category, Tag
from apps.videos.models import Video


def home(request):
    """Home page with featured videos."""
    featured_videos = Video.objects.filter(
        is_published=True,
        is_featured=True
    ).select_related('user', 'category').prefetch_related('tags')[:12]
    
    recent_videos = Video.objects.filter(
        is_published=True
    ).select_related('user', 'category').prefetch_related('tags')[:12]
    
    context = {
        'featured_videos': featured_videos,
        'recent_videos': recent_videos,
    }
    return render(request, 'core/home.html', context)


def search(request):
    """Search videos."""
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    sort = request.GET.get('sort', 'newest')
    
    videos = Video.objects.filter(is_published=True)
    
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
    
    paginator = Paginator(videos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'videos': page_obj,
        'query': query,
        'selected_category': category,
        'sort': sort,
    }
    return render(request, 'videos/list.html', context)


def get_categories(request):
    """Display all categories page."""
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    
    # Get video count for each category
    for category in categories:
        category.video_count = Video.objects.filter(
            category=category,
            is_published=True
        ).count()
    
    context = {
        'categories': categories,
    }
    return render(request, 'core/categories.html', context)


@require_http_methods(["GET"])
def get_tags(request):
    """Get popular tags for HTMX requests."""
    tags = Tag.objects.all()[:20]
    return render(request, 'partials/tags.html', {'tags': tags})

