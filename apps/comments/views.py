"""
Comment views for TubeCMS.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.videos.models import Video

from .forms import CommentEditForm, CommentForm, CommentReportForm
from .models import Comment, CommentLike, CommentReport


@login_required
@require_http_methods(["POST"])
def add_comment(request, video_slug):
    """Add comment to video."""
    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=video_slug
    )
    parent_id = request.POST.get("parent_id")
    parent = None

    if parent_id:
        parent = get_object_or_404(
            Comment.objects.select_related("user", "video"), id=parent_id, video=video
        )
        # Check depth limit
        if parent.depth >= 1:
            return JsonResponse({"error": "Maximum reply depth reached"}, status=400)

    form = CommentForm(request.POST, user=request.user, video=video, parent=parent)

    if form.is_valid():
        comment = form.save()

        # Update video comment count
        from django.db.models import F

        Video.objects.filter(pk=video.pk).update(comments_count=F("comments_count") + 1)

        # Update parent replies count
        if parent:
            parent.replies_count += 1
            parent.save(update_fields=["replies_count"])

        return render(
            request,
            "comments/htmx/comment_item.html",
            {"comment": comment, "is_new": True},
        )
    else:
        return JsonResponse({"error": "Invalid comment data"}, status=400)


@login_required
@require_http_methods(["POST"])
def edit_comment(request, comment_id):
    """Edit comment."""
    comment = get_object_or_404(
        Comment.objects.select_related("user", "video", "parent"),
        id=comment_id,
        user=request.user,
    )

    form = CommentEditForm(request.POST, instance=comment)

    if form.is_valid():
        form.save()
        return render(
            request,
            "comments/htmx/comment_item.html",
            {"comment": comment, "is_edited": True},
        )
    else:
        return JsonResponse({"error": "Invalid comment data"}, status=400)


@login_required
@require_http_methods(["POST"])
def delete_comment(request, comment_id):
    """Delete comment."""
    comment = get_object_or_404(
        Comment.objects.select_related("user", "video", "parent"),
        id=comment_id,
        user=request.user,
    )
    video = comment.video
    parent = comment.parent

    # Update counts
    from django.db.models import F

    Video.objects.filter(pk=video.pk).update(comments_count=F("comments_count") - 1)

    if parent:
        parent.replies_count = max(0, parent.replies_count - 1)
        parent.save(update_fields=["replies_count"])

    comment.delete()

    return JsonResponse({"status": "deleted"})


@login_required
@require_http_methods(["POST"])
def like_comment(request, comment_id):
    """Like/dislike comment."""
    from django.db.models import F

    comment = get_object_or_404(
        Comment.objects.select_related("user", "video"), id=comment_id
    )
    value = int(request.POST.get("value", 1))

    like, created = CommentLike.objects.get_or_create(
        user=request.user, comment=comment, defaults={"value": value}
    )

    if not created:
        if like.value == value:
            # Remove like/dislike - атомарно уменьшаем счетчик
            like.delete()
            Comment.objects.filter(pk=comment.pk).update(
                likes_count=F("likes_count") - 1
            )
        else:
            # Change like/dislike - счетчик не меняется, только значение
            like.value = value
            like.save()
    else:
        # New like/dislike - атомарно увеличиваем счетчик
        Comment.objects.filter(pk=comment.pk).update(likes_count=F("likes_count") + 1)

    # Обновляем локальный объект
    comment.refresh_from_db()

    return render(request, "comments/htmx/comment_likes.html", {"comment": comment})


@require_http_methods(["POST"])
def report_comment(request, comment_id):
    """Report comment."""
    comment = get_object_or_404(
        Comment.objects.select_related("user", "video"), id=comment_id
    )

    if request.method == "POST":
        form = CommentReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.comment = comment
            report.user = request.user if request.user.is_authenticated else None
            report.save()

            return JsonResponse({"status": "reported"})
        else:
            return JsonResponse({"error": "Invalid report data"}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@require_http_methods(["GET"])
def get_comments(request, video_slug):
    """Get comments for video."""
    from apps.videos.constants import COMMENTS_PER_PAGE

    video = get_object_or_404(
        Video.objects.select_related("created_by", "category"), slug=video_slug
    )

    # Get top-level comments with prefetch for likes
    comments = (
        Comment.objects.filter(video=video, parent=None)
        .select_related("user")
        .prefetch_related("replies__user", "likes")
        .order_by("-created_at")
    )

    # Pagination
    paginator = Paginator(comments, COMMENTS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "comments/htmx/comments_list.html",
        {"comments": page_obj, "video": video},
    )


@require_http_methods(["GET"])
def get_replies(request, comment_id):
    """Get replies for comment."""
    comment = get_object_or_404(
        Comment.objects.select_related("user", "video", "parent"), id=comment_id
    )
    replies = comment.get_replies().select_related("user")

    return render(
        request,
        "comments/htmx/replies_list.html",
        {"replies": replies, "parent_comment": comment},
    )
