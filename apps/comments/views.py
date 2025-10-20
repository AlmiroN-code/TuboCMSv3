"""
Comment views for TubeCMS.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Count

from .models import Comment, CommentLike, CommentReport
from .forms import CommentForm, CommentEditForm, CommentReportForm
from apps.videos.models import Video


@login_required
@require_http_methods(["POST"])
def add_comment(request, video_slug):
    """Add comment to video."""
    video = get_object_or_404(Video, slug=video_slug)
    parent_id = request.POST.get('parent_id')
    parent = None
    
    if parent_id:
        parent = get_object_or_404(Comment, id=parent_id, video=video)
        # Check depth limit
        if parent.depth >= 1:
            return JsonResponse({'error': 'Maximum reply depth reached'}, status=400)
    
    form = CommentForm(request.POST, user=request.user, video=video, parent=parent)
    
    if form.is_valid():
        comment = form.save()
        
        # Update video comment count
        video.comments_count += 1
        video.save(update_fields=['comments_count'])
        
        # Update parent replies count
        if parent:
            parent.replies_count += 1
            parent.save(update_fields=['replies_count'])
        
        return render(request, 'comments/htmx/comment_item.html', {
            'comment': comment,
            'is_new': True
        })
    else:
        return JsonResponse({'error': 'Invalid comment data'}, status=400)


@login_required
@require_http_methods(["POST"])
def edit_comment(request, comment_id):
    """Edit comment."""
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    
    form = CommentEditForm(request.POST, instance=comment)
    
    if form.is_valid():
        form.save()
        return render(request, 'comments/htmx/comment_item.html', {
            'comment': comment,
            'is_edited': True
        })
    else:
        return JsonResponse({'error': 'Invalid comment data'}, status=400)


@login_required
@require_http_methods(["POST"])
def delete_comment(request, comment_id):
    """Delete comment."""
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    video = comment.video
    parent = comment.parent
    
    # Update counts
    video.comments_count = max(0, video.comments_count - 1)
    video.save(update_fields=['comments_count'])
    
    if parent:
        parent.replies_count = max(0, parent.replies_count - 1)
        parent.save(update_fields=['replies_count'])
    
    comment.delete()
    
    return JsonResponse({'status': 'deleted'})


@login_required
@require_http_methods(["POST"])
def like_comment(request, comment_id):
    """Like/dislike comment."""
    comment = get_object_or_404(Comment, id=comment_id)
    value = int(request.POST.get('value', 1))
    
    like, created = CommentLike.objects.get_or_create(
        user=request.user,
        comment=comment,
        defaults={'value': value}
    )
    
    if not created:
        if like.value == value:
            # Remove like/dislike
            like.delete()
            if value == 1:
                comment.likes_count = max(0, comment.likes_count - 1)
            else:
                comment.likes_count = max(0, comment.likes_count - 1)
        else:
            # Change like/dislike
            old_value = like.value
            like.value = value
            like.save()
            
            if old_value == 1:
                comment.likes_count = max(0, comment.likes_count - 1)
            else:
                comment.likes_count = max(0, comment.likes_count - 1)
            
            if value == 1:
                comment.likes_count += 1
            else:
                comment.likes_count += 1
    else:
        # New like/dislike
        if value == 1:
            comment.likes_count += 1
        else:
            comment.likes_count += 1
    
    comment.save(update_fields=['likes_count'])
    
    return render(request, 'comments/htmx/comment_likes.html', {
        'comment': comment,
        'user_like': value if created or like.value == value else 0
    })


@require_http_methods(["POST"])
def report_comment(request, comment_id):
    """Report comment."""
    comment = get_object_or_404(Comment, id=comment_id)
    
    if request.method == 'POST':
        form = CommentReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.comment = comment
            report.user = request.user if request.user.is_authenticated else None
            report.save()
            
            return JsonResponse({'status': 'reported'})
        else:
            return JsonResponse({'error': 'Invalid report data'}, status=400)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@require_http_methods(["GET"])
def get_comments(request, video_slug):
    """Get comments for video."""
    video = get_object_or_404(Video, slug=video_slug)
    
    # Get top-level comments
    comments = Comment.objects.filter(
        video=video,
        parent=None
    ).select_related('user').prefetch_related('replies__user').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(comments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'comments/htmx/comments_list.html', {
        'comments': page_obj,
        'video': video
    })


@require_http_methods(["GET"])
def get_replies(request, comment_id):
    """Get replies for comment."""
    comment = get_object_or_404(Comment, id=comment_id)
    replies = comment.get_replies().select_related('user')
    
    return render(request, 'comments/htmx/replies_list.html', {
        'replies': replies,
        'parent_comment': comment
    })











