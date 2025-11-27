"""
HTMX-specific views for comments.
"""
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from ..forms import CommentEditForm, CommentForm, CommentReportForm
from ..models import Comment, CommentLike


@require_http_methods(["GET"])
def comment_form(request, video_slug, parent_id=None):
    """HTMX comment form."""
    from apps.videos.models import Video

    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=video_slug
    )
    parent = None

    if parent_id:
        parent = get_object_or_404(
            Comment.objects.select_related("user", "video"), id=parent_id, video=video
        )

    form = CommentForm()

    return render(
        request,
        "comments/htmx/comment_form.html",
        {"form": form, "video": video, "parent": parent},
    )


@require_http_methods(["POST"])
def comment_create(request, video_slug, parent_id=None):
    """HTMX create comment."""
    from apps.videos.models import Video

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=video_slug
    )
    parent = None

    if parent_id:
        parent = get_object_or_404(
            Comment.objects.select_related("user", "video"), id=parent_id, video=video
        )

    form = CommentForm(request.POST, user=request.user, video=video, parent=parent)

    if form.is_valid():
        comment = form.save()

        # Update comment count
        from django.db.models import F

        Video.objects.filter(pk=video.pk).update(comments_count=F("comments_count") + 1)

        if parent:
            parent.replies_count += 1
            parent.save(update_fields=["replies_count"])

        return render(request, "comments/htmx/comment_item.html", {"comment": comment})
    else:
        # Return form with errors for HTMX
        return render(
            request,
            "comments/htmx/comment_form.html",
            {"form": form, "video": video, "parent": parent},
            status=400,
        )


@require_http_methods(["GET"])
def comment_edit_form(request, comment_id):
    """HTMX comment edit form."""
    comment = get_object_or_404(
        Comment.objects.select_related("user", "video", "parent"),
        id=comment_id,
        user=request.user,
    )

    form = CommentEditForm(instance=comment)

    return render(
        request,
        "comments/htmx/comment_edit_form.html",
        {"form": form, "comment": comment},
    )


@require_http_methods(["GET"])
def comment_replies(request, comment_id):
    """HTMX comment replies."""
    comment = get_object_or_404(
        Comment.objects.select_related("user", "video", "parent"), id=comment_id
    )
    replies = comment.get_replies().select_related("user")

    return render(
        request,
        "comments/htmx/comment_replies.html",
        {"replies": replies, "parent_comment": comment},
    )


@require_http_methods(["GET"])
def comment_report_form(request, comment_id):
    """HTMX comment report form."""
    comment = get_object_or_404(
        Comment.objects.select_related("user", "video"), id=comment_id
    )

    form = CommentReportForm()

    return render(
        request,
        "comments/htmx/comment_report_form.html",
        {"form": form, "comment": comment},
    )


@require_http_methods(["GET"])
def comment_likes(request, comment_id):
    """HTMX comment likes."""
    comment = get_object_or_404(
        Comment.objects.select_related("user", "video"), id=comment_id
    )

    return render(request, "comments/htmx/comment_likes.html", {"comment": comment})
