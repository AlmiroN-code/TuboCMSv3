"""
Optimized managers for Comment models.
"""
from django.db import models
from django.db.models import Count, Prefetch, Q


class CommentQuerySet(models.QuerySet):
    """Optimized queryset for Comment model."""

    def with_related(self):
        """Prefetch all related data to avoid N+1 queries."""
        return self.select_related("user", "video", "parent").prefetch_related(
            "likes__user", "replies__user"
        )

    def with_stats(self):
        """Annotate with statistics."""
        return self.annotate(
            likes_count=Count("likes", filter=Q(likes__value=1)),
            dislikes_count=Count("likes", filter=Q(likes__value=-1)),
            replies_count=Count("replies"),
        )

    def top_level(self):
        """Get only top-level comments (not replies)."""
        return self.filter(parent=None)

    def for_video(self, video):
        """Get comments for specific video."""
        return self.filter(video=video)

    def recent(self):
        """Get recent comments."""
        return self.order_by("-created_at")

    def popular(self):
        """Get popular comments ordered by likes."""
        return self.with_stats().order_by("-likes_count", "-created_at")

    def with_replies(self):
        """Prefetch replies with optimized query."""
        return self.prefetch_related(
            Prefetch(
                "replies",
                queryset=models.Model.objects.select_related("user").order_by(
                    "created_at"
                ),
            )
        )


class CommentManager(models.Manager):
    """Optimized manager for Comment model."""

    def get_queryset(self):
        return CommentQuerySet(self.model, using=self._db)

    def with_related(self):
        return self.get_queryset().with_related()

    def with_stats(self):
        return self.get_queryset().with_stats()

    def top_level(self):
        return self.get_queryset().top_level()

    def for_video(self, video):
        return self.get_queryset().for_video(video)

    def recent(self):
        return self.get_queryset().recent()

    def popular(self):
        return self.get_queryset().popular()

    def with_replies(self):
        return self.get_queryset().with_replies()

    def for_video_optimized(self, video, limit=20):
        """Get optimized comments for video page."""
        return (
            self.top_level()
            .for_video(video)
            .with_related()
            .with_stats()
            .with_replies()
            .recent()[:limit]
        )


class CommentLikeQuerySet(models.QuerySet):
    """Optimized queryset for CommentLike model."""

    def with_related(self):
        """Prefetch related data."""
        return self.select_related("user", "comment")

    def likes(self):
        """Get only likes."""
        return self.filter(value=1)

    def dislikes(self):
        """Get only dislikes."""
        return self.filter(value=-1)


class CommentLikeManager(models.Manager):
    """Optimized manager for CommentLike model."""

    def get_queryset(self):
        return CommentLikeQuerySet(self.model, using=self._db)

    def with_related(self):
        return self.get_queryset().with_related()

    def likes(self):
        return self.get_queryset().likes()

    def dislikes(self):
        return self.get_queryset().dislikes()
