"""
HTMX-specific views for comments.
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator

from ..models import Comment, CommentLike
from ..forms import CommentForm, CommentEditForm, CommentReportForm


@require_http_methods(["GET"])
def comment_form(request, video_slug, parent_id=None):
    """HTMX comment form."""
    from apps.videos.models import Video
    
    video = get_object_or_404(Video, slug=video_slug)
    parent = None
    
    if parent_id:
        parent = get_object_or_404(Comment, id=parent_id, video=video)
    
    form = CommentForm()
    
    return render(request, 'comments/htmx/comment_form.html', {
        'form': form,
        'video': video,
        'parent': parent
    })


@require_http_methods(["POST"])
def comment_create(request, video_slug, parent_id=None):
    """HTMX create comment."""
    from apps.videos.models import Video
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    video = get_object_or_404(Video, slug=video_slug)
    parent = None
    
    if parent_id:
        parent = get_object_or_404(Comment, id=parent_id, video=video)
    
    form = CommentForm(request.POST, user=request.user, video=video, parent=parent)
    
    if form.is_valid():
        comment = form.save()
        
        # Update comment count
        video.comments_count += 1
        video.save(update_fields=['comments_count'])
        
        if parent:
            parent.replies_count += 1
            parent.save(update_fields=['replies_count'])
        
        return render(request, 'comments/htmx/comment_item.html', {
            'comment': comment,
            'user_like': 0
        })
    else:
        return JsonResponse({'error': 'Invalid form data'}, status=400)


@require_http_methods(["GET"])
def comment_edit_form(request, comment_id):
    """HTMX comment edit form."""
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    
    form = CommentEditForm(instance=comment)
    
    return render(request, 'comments/htmx/comment_edit_form.html', {
        'form': form,
        'comment': comment
    })


@require_http_methods(["GET"])
def comment_replies(request, comment_id):
    """HTMX comment replies."""
    comment = get_object_or_404(Comment, id=comment_id)
    replies = comment.get_replies().select_related('user')
    
    return render(request, 'comments/htmx/comment_replies.html', {
        'replies': replies,
        'parent_comment': comment
    })


@require_http_methods(["GET"])
def comment_report_form(request, comment_id):
    """HTMX comment report form."""
    comment = get_object_or_404(Comment, id=comment_id)
    
    form = CommentReportForm()
    
    return render(request, 'comments/htmx/comment_report_form.html', {
        'form': form,
        'comment': comment
    })


@require_http_methods(["GET"])
def comment_likes(request, comment_id):
    """HTMX comment likes."""
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Get user's like status
    user_like = None
    if request.user.is_authenticated:
        try:
            like = CommentLike.objects.get(comment=comment, user=request.user)
            user_like = like.value
        except CommentLike.DoesNotExist:
            user_like = 0
    
    return render(request, 'comments/htmx/comment_likes.html', {
        'comment': comment,
        'user_like': user_like
    })
