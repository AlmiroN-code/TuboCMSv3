"""
User views for TubeCMS.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q

from .models import User, UserProfile, Subscription
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm, UserSettingsForm
from apps.videos.models import Video


def register(request):
    """User registration."""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # Check if user registered as model
            if form.cleaned_data.get('register_as_model'):
                messages.success(request, 'Регистрация прошла успешно! Профиль модели создан. Вы можете добавить видео в админке.')
            else:
                messages.success(request, 'Регистрация прошла успешно!')
            
            return redirect('core:home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/register.html', {'form': form})


def user_login(request):
    """User login."""
    if request.user.is_authenticated:
        return redirect('core:home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('core:home')
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'users/login.html', {'form': form})


@login_required
def user_logout(request):
    """User logout."""
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('core:home')


@login_required
def profile(request, username):
    """User profile page."""
    user = get_object_or_404(User, username=username)
    videos = Video.objects.filter(user=user, is_published=True).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(videos, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Check if current user is subscribed to this user
    is_subscribed = False
    if request.user.is_authenticated and request.user != user:
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user, 
            channel=user
        ).exists()
    
    context = {
        'profile_user': user,
        'videos': page_obj,
        'is_subscribed': is_subscribed,
    }
    return render(request, 'users/profile.html', context)


@login_required
def edit_profile(request):
    """Edit user profile."""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлен!')
            return redirect('users:profile', username=request.user.username)
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'users/profile_edit.html', {'form': form})


@login_required
def user_settings(request):
    """User settings page."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Настройки сохранены!')
            return redirect('users:settings')
    else:
        form = UserSettingsForm(instance=profile)
    
    return render(request, 'users/settings.html', {'form': form})


@login_required
@require_http_methods(["POST"])
def subscribe(request, username):
    """Subscribe to a user."""
    channel = get_object_or_404(User, username=username)
    
    if request.user == channel:
        return JsonResponse({'error': 'Cannot subscribe to yourself'}, status=400)
    
    subscription, created = Subscription.objects.get_or_create(
        subscriber=request.user,
        channel=channel
    )
    
    if created:
        # Update subscriber count
        channel.subscribers_count += 1
        channel.save(update_fields=['subscribers_count'])
        
        return JsonResponse({
            'status': 'subscribed',
            'subscribers_count': channel.subscribers_count
        })
    else:
        return JsonResponse({'error': 'Already subscribed'}, status=400)


@login_required
@require_http_methods(["POST"])
def unsubscribe(request, username):
    """Unsubscribe from a user."""
    channel = get_object_or_404(User, username=username)
    
    try:
        subscription = Subscription.objects.get(
            subscriber=request.user,
            channel=channel
        )
        subscription.delete()
        
        # Update subscriber count
        channel.subscribers_count = max(0, channel.subscribers_count - 1)
        channel.save(update_fields=['subscribers_count'])
        
        return JsonResponse({
            'status': 'unsubscribed',
            'subscribers_count': channel.subscribers_count
        })
    except Subscription.DoesNotExist:
        return JsonResponse({'error': 'Not subscribed'}, status=400)


@login_required
def subscriptions(request):
    """User's subscriptions."""
    subscriptions = Subscription.objects.filter(subscriber=request.user).select_related('channel')
    
    # Get recent videos from subscribed channels
    subscribed_channels = [sub.channel for sub in subscriptions]
    recent_videos = Video.objects.filter(
        user__in=subscribed_channels,
        is_published=True
    ).select_related('user', 'category').order_by('-created_at')[:20]
    
    context = {
        'subscriptions': subscriptions,
        'recent_videos': recent_videos,
    }
    return render(request, 'users/subscriptions.html', context)






