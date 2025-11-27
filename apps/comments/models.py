"""
Comment models for TubeCMS.
"""
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.videos.models import Video

from .managers import CommentLikeManager, CommentManager

User = get_user_model()


class Comment(models.Model):
    """Video comments with nested structure."""

    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    content = models.TextField()
    is_edited = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    likes_count = models.PositiveIntegerField(default=0)
    replies_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = CommentManager()

    class Meta:
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["video", "parent"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.video.title}"

    @property
    def is_reply(self):
        """Check if comment is a reply."""
        return self.parent is not None

    @property
    def depth(self):
        """Get comment depth (0 for top-level, 1 for replies)."""
        if self.parent is None:
            return 0
        return 1  # Only 2 levels allowed

    def get_replies(self):
        """Get direct replies to this comment."""
        return self.replies.filter(parent=self).order_by("created_at")

    def get_all_replies(self):
        """Get all replies recursively."""
        replies = []
        for reply in self.get_replies():
            replies.append(reply)
            replies.extend(reply.get_all_replies())
        return replies


class CommentLike(models.Model):
    """Comment likes."""

    LIKE_CHOICES = [
        (1, "Like"),
        (-1, "Dislike"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comment_likes"
    )
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    value = models.SmallIntegerField(choices=LIKE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    # Managers
    objects = CommentLikeManager()

    class Meta:
        unique_together = ["user", "comment"]
        verbose_name = "Comment Like"
        verbose_name_plural = "Comment Likes"

    def __str__(self):
        return f"{self.user.username} {'liked' if self.value == 1 else 'disliked'} comment {self.comment.id}"


class CommentReport(models.Model):
    """Comment reports."""

    REPORT_TYPES = [
        ("spam", "Spam"),
        ("inappropriate", "Inappropriate Content"),
        ("harassment", "Harassment"),
        ("hate_speech", "Hate Speech"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comment_reports"
    )
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name="reports"
    )
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "comment"]
        verbose_name = "Comment Report"
        verbose_name_plural = "Comment Reports"

    def __str__(self):
        return f"Report of comment {self.comment.id} by {self.user.username}"
