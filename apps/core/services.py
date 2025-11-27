"""
Core services for caching and performance optimization.
"""
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q


class CacheService:
    """Service for managing cache operations."""

    # Cache timeouts
    SHORT_TIMEOUT = 300  # 5 minutes
    MEDIUM_TIMEOUT = 1800  # 30 minutes
    LONG_TIMEOUT = 3600  # 1 hour
    VERY_LONG_TIMEOUT = 86400  # 24 hours

    @staticmethod
    def get_or_set(key, callable_func, timeout=SHORT_TIMEOUT):
        """Get from cache or set if not exists."""
        data = cache.get(key)
        if data is None:
            data = callable_func()
            cache.set(key, data, timeout)
        return data

    @staticmethod
    def invalidate_pattern(pattern):
        """Invalidate cache keys matching pattern."""
        # Для Redis можно использовать SCAN
        try:
            from django_redis import get_redis_connection

            redis_conn = get_redis_connection("default")
            keys = redis_conn.keys(f"*{pattern}*")
            if keys:
                redis_conn.delete(*keys)
        except ImportError:
            # Fallback для других кэш-бэкендов
            pass

    @classmethod
    def get_categories_cached(cls):
        """Get active categories with video counts."""

        def _get_categories():
            from .models import Category

            return list(
                Category.objects.filter(is_active=True)
                .annotate(
                    video_count=Count("video", filter=Q(video__status="published"))
                )
                .order_by("order", "name")
            )

        return cls.get_or_set("categories_active", _get_categories, cls.LONG_TIMEOUT)

    @classmethod
    def get_site_settings_cached(cls):
        """Get active site settings."""

        def _get_settings():
            from .models import SiteSettings

            try:
                return SiteSettings.objects.filter(is_active=True).first()
            except SiteSettings.DoesNotExist:
                return None

        return cls.get_or_set(
            "site_settings_active", _get_settings, cls.VERY_LONG_TIMEOUT
        )

    @classmethod
    def get_seo_settings_cached(cls):
        """Get active SEO settings."""

        def _get_seo():
            from .models import SEOSettings

            try:
                return SEOSettings.objects.filter(is_active=True).first()
            except SEOSettings.DoesNotExist:
                return None

        return cls.get_or_set("seo_settings_active", _get_seo, cls.VERY_LONG_TIMEOUT)

    @classmethod
    def invalidate_settings_cache(cls):
        """Invalidate all settings cache."""
        cache.delete_many(
            ["site_settings_active", "seo_settings_active", "categories_active"]
        )


class VideoStatsService:
    """Service for video statistics and performance."""

    @staticmethod
    def get_video_stats_cached(video_id, timeout=CacheService.SHORT_TIMEOUT):
        """Get cached video statistics."""
        cache_key = f"video_stats_{video_id}"

        def _get_stats():
            from apps.videos.models import Rating, Video

            try:
                video = Video.objects.get(id=video_id)
                likes = Rating.objects.filter(video=video, value=1).count()
                dislikes = Rating.objects.filter(video=video, value=-1).count()
                comments = video.comments.filter(parent=None).count()

                return {
                    "likes": likes,
                    "dislikes": dislikes,
                    "comments": comments,
                    "views": video.views_count,
                    "rating_percentage": (likes / (likes + dislikes) * 100)
                    if (likes + dislikes) > 0
                    else 0,
                }
            except Video.DoesNotExist:
                return None

        return CacheService.get_or_set(cache_key, _get_stats, timeout)

    @staticmethod
    def invalidate_video_stats(video_id):
        """Invalidate video statistics cache."""
        cache.delete(f"video_stats_{video_id}")

    @staticmethod
    def get_trending_videos_cached(days=7, limit=20):
        """Get cached trending videos."""
        cache_key = f"trending_videos_{days}_{limit}"

        def _get_trending():
            from apps.videos.models import Video

            return list(Video.objects.published().with_related().trending(days)[:limit])

        return CacheService.get_or_set(
            cache_key, _get_trending, CacheService.MEDIUM_TIMEOUT
        )

    @staticmethod
    def get_popular_videos_cached(limit=20):
        """Get cached popular videos."""
        cache_key = f"popular_videos_{limit}"

        def _get_popular():
            from apps.videos.models import Video

            return list(Video.objects.published().with_related().popular()[:limit])

        return CacheService.get_or_set(
            cache_key, _get_popular, CacheService.MEDIUM_TIMEOUT
        )


class SearchService:
    """Service for search optimization."""

    @staticmethod
    def search_videos_cached(query, category=None, sort="newest", limit=100):
        """Cached video search with basic parameters."""
        # Создаем ключ кэша на основе параметров поиска
        cache_key = f"search_{hash(query)}_{category}_{sort}_{limit}"

        def _search():
            from apps.videos.models import Video

            videos = Video.objects.published().with_related()

            if query:
                videos = videos.search(query)

            if category:
                videos = videos.by_category(category)

            if sort == "popular":
                videos = videos.popular()
            elif sort == "trending":
                videos = videos.trending()
            else:
                videos = videos.recent()

            return list(videos[:limit])

        # Кэшируем поисковые запросы на короткое время
        return CacheService.get_or_set(cache_key, _search, CacheService.SHORT_TIMEOUT)

    @staticmethod
    def get_search_suggestions_cached(query, limit=10):
        """Get cached search suggestions."""
        if len(query) < 2:
            return []

        cache_key = f"search_suggestions_{hash(query)}_{limit}"

        def _get_suggestions():
            from apps.core.models import Tag
            from apps.videos.models import Video

            # Поиск в названиях видео
            video_titles = (
                Video.objects.published()
                .filter(title__icontains=query)
                .values_list("title", flat=True)[: limit // 2]
            )

            # Поиск в тегах
            tag_names = Tag.objects.filter(name__icontains=query).values_list(
                "name", flat=True
            )[: limit // 2]

            suggestions = list(video_titles) + list(tag_names)
            return suggestions[:limit]

        return CacheService.get_or_set(
            cache_key, _get_suggestions, CacheService.MEDIUM_TIMEOUT
        )
