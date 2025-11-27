"""
Cache utilities for TubeCMS search functionality.
"""
import hashlib
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone


def get_cache_key(prefix, *args, **kwargs):
    """Generate a cache key from prefix and arguments."""
    key_parts = [str(prefix)]
    key_parts.extend([str(arg) for arg in args])
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    key_string = ":".join(key_parts)

    # Hash long keys to avoid cache key length limits
    if len(key_string) > 200:
        key_string = hashlib.md5(key_string.encode()).hexdigest()

    return key_string


def cache_search_results(query, search_type="all", limit=8, timeout=300):
    """Cache search results for better performance."""
    cache_key = get_cache_key("search", query, search_type, limit)
    cached_results = cache.get(cache_key)

    if cached_results is not None:
        return cached_results

    from django.apps import apps

    Video = apps.get_model("videos", "Video")
    User = apps.get_model("users", "User")
    Category = apps.get_model("core", "Category")
    Tag = apps.get_model("core", "Tag")

    results = {}

    # Search videos
    if search_type in ["all", "videos"]:
        videos = (
            Video.objects.filter(status="published")
            .select_related("created_by", "category")
            .prefetch_related("tags")
            .filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(tags__name__icontains=query)
                | Q(created_by__username__icontains=query)
            )
            .distinct()[: limit if search_type == "videos" else limit // 2]
        )
        results["videos"] = list(videos)

    # Search users
    if search_type in ["all", "users"]:
        users = User.objects.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(bio__icontains=query)
        ).annotate(
            videos_count_actual=Count(
                "created_videos", filter=Q(created_videos__status="published")
            )
        )[
            : limit if search_type == "users" else 3
        ]
        results["users"] = list(users)

    # Search categories
    if search_type in ["all", "categories"]:
        categories = (
            Category.objects.filter(is_active=True)
            .filter(Q(name__icontains=query) | Q(description__icontains=query))
            .annotate(video_count=Count("video", filter=Q(video__status="published")))[
                : limit if search_type == "categories" else 3
            ]
        )
        results["categories"] = list(categories)

    # Search tags
    if search_type in ["all", "tags"]:
        tags = Tag.objects.filter(name__icontains=query).annotate(
            video_count=Count("video", filter=Q(video__status="published"))
        )[: limit if search_type == "tags" else 3]
        results["tags"] = list(tags)

    # Cache results
    cache.set(cache_key, results, timeout)
    return results


def cache_popular_searches(timeout=3600):
    """Cache popular search terms."""
    cache_key = "popular_searches"
    cached_searches = cache.get(cache_key)

    if cached_searches is not None:
        return cached_searches

    # This would typically come from search analytics
    # For now, return some default popular searches
    popular_searches = [
        "amateur",
        "teen",
        "milf",
        "anal",
        "blowjob",
        "lesbian",
        "threesome",
        "big tits",
        "big ass",
        "hardcore",
    ]

    cache.set(cache_key, popular_searches, timeout)
    return popular_searches


def cache_trending_tags(limit=20, timeout=1800):
    """Cache trending tags based on recent video uploads."""
    cache_key = f"trending_tags_{limit}"
    cached_tags = cache.get(cache_key)

    if cached_tags is not None:
        return cached_tags

    from apps.core.models import Tag

    # Get tags from videos uploaded in the last 7 days
    week_ago = timezone.now() - timedelta(days=7)

    trending_tags = (
        Tag.objects.filter(video__created_at__gte=week_ago, video__status="published")
        .annotate(
            recent_video_count=Count("video", filter=Q(video__created_at__gte=week_ago))
        )
        .order_by("-recent_video_count")[:limit]
    )

    cache.set(cache_key, list(trending_tags), timeout)
    return trending_tags


def cache_category_stats(timeout=1800):
    """Cache category statistics."""
    cache_key = "category_stats"
    cached_stats = cache.get(cache_key)

    if cached_stats is not None:
        return cached_stats

    from apps.core.models import Category

    categories = (
        Category.objects.filter(is_active=True)
        .annotate(
            video_count=Count("video", filter=Q(video__status="published")),
            recent_video_count=Count(
                "video",
                filter=Q(
                    video__status="published",
                    video__created_at__gte=timezone.now() - timedelta(days=7),
                ),
            ),
        )
        .order_by("-video_count")
    )

    cache.set(cache_key, list(categories), timeout)
    return categories


def invalidate_search_cache(pattern=None):
    """Invalidate search-related cache entries."""
    if pattern:
        # This would require a cache backend that supports pattern deletion
        # For now, we'll just delete specific known keys
        cache.delete_many(
            [
                "popular_searches",
                "category_stats",
            ]
        )

        # Delete trending tags cache
        for limit in [10, 20, 50]:
            cache.delete(f"trending_tags_{limit}")
    else:
        # Clear all search-related cache
        cache.clear()


def warm_search_cache():
    """Pre-warm frequently accessed cache entries."""
    # Warm popular searches
    cache_popular_searches()

    # Warm trending tags
    cache_trending_tags(20)

    # Warm category stats
    cache_category_stats()

    # Warm some common search queries
    common_queries = ["teen", "milf", "amateur", "anal", "lesbian"]
    for query in common_queries:
        cache_search_results(query, "all", 8, 600)  # Cache for 10 minutes
