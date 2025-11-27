"""
Optimized managers for Core models.
"""
from django.db import models
from django.db.models import Count, Q


class CategoryQuerySet(models.QuerySet):
    """Optimized queryset for Category model."""

    def active(self):
        """Get only active categories."""
        return self.filter(is_active=True)

    def with_video_counts(self):
        """Annotate with video counts."""
        return self.annotate(
            video_count=Count("video", filter=Q(video__status="published")),
            total_views=models.Sum("video__views_count"),
        )

    def popular(self):
        """Get categories ordered by video count."""
        return self.with_video_counts().order_by("-video_count", "order", "name")

    def ordered(self):
        """Get categories in display order."""
        return self.order_by("order", "name")


class CategoryManager(models.Manager):
    """Optimized manager for Category model."""

    def get_queryset(self):
        return CategoryQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def with_video_counts(self):
        return self.get_queryset().with_video_counts()

    def popular(self):
        return self.get_queryset().popular()

    def ordered(self):
        return self.get_queryset().ordered()

    def for_navigation(self):
        """Get categories optimized for navigation."""
        return self.active().with_video_counts().ordered()


class TagQuerySet(models.QuerySet):
    """Optimized queryset for Tag model."""

    def with_video_counts(self):
        """Annotate with video counts."""
        return self.annotate(
            video_count=Count("video", filter=Q(video__status="published"))
        )

    def popular(self, limit=20):
        """Get popular tags."""
        return (
            self.with_video_counts()
            .filter(video_count__gt=0)
            .order_by("-video_count", "name")[:limit]
        )

    def for_cloud(self, limit=50):
        """Get tags for tag cloud."""
        return (
            self.with_video_counts()
            .filter(video_count__gt=0)
            .order_by("-video_count")[:limit]
        )


class TagManager(models.Manager):
    """Optimized manager for Tag model."""

    def get_queryset(self):
        return TagQuerySet(self.model, using=self._db)

    def with_video_counts(self):
        return self.get_queryset().with_video_counts()

    def popular(self, limit=20):
        return self.get_queryset().popular(limit)

    def for_cloud(self, limit=50):
        return self.get_queryset().for_cloud(limit)


class SiteSettingsQuerySet(models.QuerySet):
    """Optimized queryset for SiteSettings model."""

    def active(self):
        """Get active settings."""
        return self.filter(is_active=True)


class SiteSettingsManager(models.Manager):
    """Optimized manager for SiteSettings model."""

    def get_queryset(self):
        return SiteSettingsQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def get_active(self):
        """Get the active site settings instance."""
        return self.active().first()


class SEOSettingsQuerySet(models.QuerySet):
    """Optimized queryset for SEOSettings model."""

    def active(self):
        """Get active settings."""
        return self.filter(is_active=True)


class SEOSettingsManager(models.Manager):
    """Optimized manager for SEOSettings model."""

    def get_queryset(self):
        return SEOSettingsQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def get_active(self):
        """Get the active SEO settings instance."""
        return self.active().first()
