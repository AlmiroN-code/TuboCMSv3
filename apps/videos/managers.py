"""
Optimized managers for Video models.
"""
from django.db import models
from django.db.models import Count, Prefetch, Q


class VideoQuerySet(models.QuerySet):
    """Optimized queryset for Video model."""

    def published(self):
        """Filter published videos."""
        return self.filter(status="published")

    def with_related(self):
        """Prefetch all related data to avoid N+1 queries."""
        return self.select_related("created_by", "category").prefetch_related(
            "tags", "encoded_files__profile", "ratings__user", "comments__user"
        )

    def with_stats(self):
        """Annotate with statistics."""
        return self.annotate(
            likes_count=Count("ratings", filter=Q(ratings__value=1)),
            dislikes_count=Count("ratings", filter=Q(ratings__value=-1)),
            total_comments=Count("comments", filter=Q(comments__parent=None)),
        )

    def trending(self, days=7):
        """Get trending videos from last N days."""
        from datetime import timedelta

        from django.utils import timezone

        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=cutoff_date).order_by(
            "-views_count", "-created_at"
        )

    def popular(self):
        """Get popular videos ordered by views."""
        return self.order_by("-views_count", "-created_at")

    def recent(self):
        """Get recent videos."""
        return self.order_by("-created_at")

    def by_category(self, category_slug):
        """Filter by category slug."""
        return self.filter(category__slug=category_slug)

    def search(self, query):
        """Full-text search in videos."""
        if not query:
            return self

        return self.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()


class VideoManager(models.Manager):
    """Optimized manager for Video model."""

    def get_queryset(self):
        return VideoQuerySet(self.model, using=self._db)

    def published(self):
        return self.get_queryset().published()

    def with_related(self):
        return self.get_queryset().with_related()

    def with_stats(self):
        return self.get_queryset().with_stats()

    def trending(self, days=7):
        return self.get_queryset().trending(days)

    def popular(self):
        return self.get_queryset().popular()

    def recent(self):
        return self.get_queryset().recent()

    def for_homepage(self, featured_limit=10, recent_limit=20):
        """Optimized query for homepage."""
        featured = list(
            self.published().with_related().filter(is_featured=True)[:featured_limit]
        )

        recent = list(self.published().with_related().recent()[:recent_limit])

        return {"featured": featured, "recent": recent}
