"""
Favorites and Playlists models for TubeCMS.
"""
from django.contrib.auth import get_user_model
from django.db import models

from apps.core.models import TimeStampedModel

User = get_user_model()


class Favorite(TimeStampedModel):
    """User favorites for videos."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    video = models.ForeignKey(
        "Video", on_delete=models.CASCADE, related_name="favorited_by"
    )

    class Meta:
        verbose_name = "Favorite"
        verbose_name_plural = "Favorites"
        unique_together = ["user", "video"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["video", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.video.title}"


class Playlist(TimeStampedModel):
    """User playlists."""

    PRIVACY_CHOICES = [
        ("public", "Public"),
        ("unlisted", "Unlisted"),
        ("private", "Private"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="playlists")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default="public")
    thumbnail = models.ImageField(upload_to="playlists/", blank=True, null=True)

    # Auto-generated thumbnail from first video
    auto_thumbnail = models.ImageField(
        upload_to="playlists/auto/", blank=True, null=True
    )

    class Meta:
        verbose_name = "Playlist"
        verbose_name_plural = "Playlists"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "privacy", "created_at"]),
            models.Index(fields=["privacy", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} by {self.user.username}"

    @property
    def video_count(self):
        """Get number of videos in playlist."""
        return self.playlist_videos.count()

    @property
    def total_duration(self):
        """Get total duration of all videos in playlist."""
        return sum(
            pv.video.duration for pv in self.playlist_videos.all() if pv.video.duration
        )

    @property
    def display_thumbnail(self):
        """Get thumbnail to display (custom or auto-generated)."""
        if self.thumbnail:
            return self.thumbnail
        elif self.auto_thumbnail:
            return self.auto_thumbnail
        else:
            # Get thumbnail from first video
            first_video = self.playlist_videos.first()
            if first_video and first_video.video.poster:
                return first_video.video.poster
        return None

    def update_auto_thumbnail(self):
        """Update auto-generated thumbnail from first video."""
        first_video = self.playlist_videos.first()
        if first_video and first_video.video.poster:
            # Copy the poster image to playlist auto thumbnail
            # This would need proper file handling in production
            self.auto_thumbnail = first_video.video.poster
            self.save(update_fields=["auto_thumbnail"])


class PlaylistVideo(TimeStampedModel):
    """Videos in playlists with ordering."""

    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="playlist_videos"
    )
    video = models.ForeignKey(
        "Video", on_delete=models.CASCADE, related_name="in_playlists"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Playlist Video"
        verbose_name_plural = "Playlist Videos"
        unique_together = ["playlist", "video"]
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["playlist", "order"]),
            models.Index(fields=["video"]),
        ]

    def __str__(self):
        return f"{self.video.title} in {self.playlist.title}"

    def save(self, *args, **kwargs):
        # Auto-assign order if not set
        if not self.order:
            last_video = (
                PlaylistVideo.objects.filter(playlist=self.playlist)
                .order_by("-order")
                .first()
            )
            self.order = (last_video.order + 1) if last_video else 1

        super().save(*args, **kwargs)

        # Update playlist auto thumbnail if this is the first video
        if self.order == 1:
            self.playlist.update_auto_thumbnail()


class PlaylistLike(TimeStampedModel):
    """Likes for playlists."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="playlist_likes"
    )
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="likes"
    )

    class Meta:
        verbose_name = "Playlist Like"
        verbose_name_plural = "Playlist Likes"
        unique_together = ["user", "playlist"]

    def __str__(self):
        return f"{self.user.username} liked {self.playlist.title}"


class PlaylistFollow(TimeStampedModel):
    """Following playlists from other users."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="followed_playlists"
    )
    playlist = models.ForeignKey(
        Playlist, on_delete=models.CASCADE, related_name="followers"
    )

    class Meta:
        verbose_name = "Playlist Follow"
        verbose_name_plural = "Playlist Follows"
        unique_together = ["user", "playlist"]

    def __str__(self):
        return f"{self.user.username} follows {self.playlist.title}"
