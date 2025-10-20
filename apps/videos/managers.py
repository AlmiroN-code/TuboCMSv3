"""
Custom managers for Video model.
"""
from django.db import models
from django.db.models import Q, Count, Avg


class VideoManager(models.Manager):
    """Custom manager for Video model."""
    
    def published(self):
        """Return only published videos."""
        return self.filter(is_published=True, status='published')
    
    def featured(self):
        """Return featured videos."""
        return self.published().filter(is_featured=True)
    
    def by_category(self, category_slug):
        """Return videos by category."""
        return self.published().filter(category__slug=category_slug)
    
    def by_user(self, user):
        """Return videos by user."""
        return self.filter(user=user)
    
    def search(self, query):
        """Search videos by title, description, and tags."""
        return self.published().filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()
    
    def popular(self):
        """Return popular videos ordered by views."""
        return self.published().order_by('-views_count', '-created_at')
    
    def recent(self):
        """Return recent videos."""
        return self.published().order_by('-created_at')
    
    def trending(self):
        """Return trending videos (high views in recent time)."""
        from django.utils import timezone
        from datetime import timedelta
        
        # Videos with high views in last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        return self.published().filter(
            created_at__gte=week_ago
        ).order_by('-views_count', '-created_at')
    
    def recommended(self, user, limit=10):
        """Return recommended videos for user."""
        if not user.is_authenticated:
            return self.popular()[:limit]
        
        # Get user's liked categories
        liked_categories = self.filter(
            user=user,
            likes__value=1
        ).values_list('category', flat=True).distinct()
        
        # Get videos from liked categories
        if liked_categories:
            return self.published().filter(
                category__in=liked_categories
            ).exclude(user=user).order_by('-views_count')[:limit]
        
        # Fallback to popular videos
        return self.popular()[:limit]


class VideoQuerySet(models.QuerySet):
    """Custom queryset for Video model."""
    
    def with_stats(self):
        """Annotate with statistics."""
        return self.annotate(
            total_likes=models.Count('likes', filter=Q(likes__value=1)),
            total_dislikes=models.Count('likes', filter=Q(likes__value=-1)),
            total_views=models.Count('video_views'),
        )
    
    def with_user_info(self):
        """Select related user information."""
        return self.select_related('user', 'category').prefetch_related('tags')
    
    def by_date_range(self, start_date, end_date):
        """Filter by date range."""
        return self.filter(created_at__range=[start_date, end_date])
    
    def by_duration_range(self, min_duration, max_duration):
        """Filter by duration range."""
        return self.filter(duration__range=[min_duration, max_duration])










