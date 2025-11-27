"""
Optimized managers for User models.
"""
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.db.models import Count, Prefetch, Q


class UserQuerySet(models.QuerySet):
    """Optimized queryset for User model."""

    def with_profile_data(self):
        """Prefetch profile related data."""
        return self.select_related("profile").prefetch_related(
            "subscriptions__channel", "subscribers__subscriber"
        )

    def with_video_stats(self):
        """Annotate with video statistics."""
        return self.annotate(
            videos_count=Count(
                "created_videos", filter=Q(created_videos__status="published")
            ),
            total_views=models.Sum("created_videos__views_count"),
            subscribers_count=Count("subscribers"),
        )

    def with_activity_data(self):
        """Prefetch activity related data."""
        return self.prefetch_related(
            Prefetch(
                "created_videos",
                queryset=models.Model.objects.select_related("category")
                .filter(status="published")
                .order_by("-created_at")[:10],
            ),
            Prefetch(
                "notifications",
                queryset=models.Model.objects.filter(is_read=False).order_by(
                    "-created_at"
                )[:5],
            ),
        )

    def active_creators(self):
        """Get active video creators."""
        return (
            self.filter(created_videos__status="published")
            .annotate(videos_count=Count("created_videos"))
            .filter(videos_count__gt=0)
            .distinct()
        )


class UserManager(BaseUserManager):
    """Optimized manager for User model."""

    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def create_user(self, email, username, password=None, **extra_fields):
        """Create and return a regular user."""
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)

    def with_profile_data(self):
        return self.get_queryset().with_profile_data()

    def with_video_stats(self):
        return self.get_queryset().with_video_stats()

    def with_activity_data(self):
        return self.get_queryset().with_activity_data()

    def active_creators(self):
        return self.get_queryset().active_creators()


class SubscriptionQuerySet(models.QuerySet):
    """Optimized queryset for Subscription model."""

    def with_related(self):
        """Prefetch related data."""
        return self.select_related("subscriber", "channel")

    def for_user(self, user):
        """Get subscriptions for specific user."""
        return self.filter(subscriber=user).with_related()


class SubscriptionManager(models.Manager):
    """Optimized manager for Subscription model."""

    def get_queryset(self):
        return SubscriptionQuerySet(self.model, using=self._db)

    def with_related(self):
        return self.get_queryset().with_related()

    def for_user(self, user):
        return self.get_queryset().for_user(user)


class NotificationQuerySet(models.QuerySet):
    """Optimized queryset for Notification model."""

    def with_related(self):
        """Prefetch related data."""
        return self.select_related("recipient", "sender")

    def unread(self):
        """Get unread notifications."""
        return self.filter(is_read=False)

    def for_user(self, user):
        """Get notifications for specific user."""
        return self.filter(recipient=user).with_related()

    def recent(self, limit=10):
        """Get recent notifications."""
        return self.order_by("-created_at")[:limit]


class NotificationManager(models.Manager):
    """Optimized manager for Notification model."""

    def get_queryset(self):
        return NotificationQuerySet(self.model, using=self._db)

    def with_related(self):
        return self.get_queryset().with_related()

    def unread(self):
        return self.get_queryset().unread()

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def recent(self, limit=10):
        return self.get_queryset().recent(limit)
