"""
User views for TubeCMS.
"""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetConfirmView
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from apps.videos.models import Video

from .forms import (
    CustomAuthenticationForm,
    CustomUserCreationForm,
    PasswordChangeForm,
    ProfileEditForm,
    UserProfileForm,
    UserSettingsForm,
)
from .models import Friendship, Notification, Subscription, User, UserProfile


def register(request):
    """User registration."""
    from apps.core.utils import get_site_settings

    site_settings = get_site_settings()

    if request.user.is_authenticated:
        return redirect("core:home")

    # Проверяем, разрешена ли регистрация
    if site_settings and not site_settings.allow_registration:
        messages.error(request, "Регистрация новых пользователей временно отключена.")
        return redirect("core:home")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            # Check if user registered as model
            if form.cleaned_data.get("register_as_model"):
                messages.success(
                    request,
                    "Регистрация прошла успешно! Профиль модели создан. Вы можете добавить видео в админке.",
                )
            else:
                messages.success(request, "Регистрация прошла успешно!")

            return redirect("core:home")
    else:
        form = CustomUserCreationForm()

    return render(
        request, "users/register.html", {"form": form, "site_settings": site_settings}
    )


def user_login(request):
    """User login."""
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Добро пожаловать, {user.username}!")
            return redirect("core:home")
    else:
        form = CustomAuthenticationForm()

    return render(request, "users/login.html", {"form": form})


@login_required
def user_logout(request):
    """User logout."""
    logout(request)
    messages.info(request, "Вы вышли из системы.")
    return redirect("core:home")


def profile(request, username):
    """User profile page - redirect to videos tab by default."""
    return redirect("members:videos", username=username)


@login_required
def edit_profile(request):
    """Edit user profile (old URL - redirect to new)."""
    return redirect("members:edit_profile", username=request.user.username)


@login_required
def edit_profile_member(request, username):
    """Edit user profile at /members/{username}/edit/."""
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    # Проверяем права доступа - только сам пользователь может редактировать свой профиль
    if request.user != profile_user:
        messages.error(request, "У вас нет прав для редактирования этого профиля.")
        return redirect("members:profile", username=username)

    profile_form = ProfileEditForm(instance=request.user)
    password_form = PasswordChangeForm(user=request.user)

    if request.method == "POST":
        # Определяем, какая форма была отправлена
        if "edit_profile" in request.POST:
            profile_form = ProfileEditForm(
                request.POST, request.FILES, instance=request.user
            )
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Профиль успешно обновлен!")
                # Если изменился username, перенаправляем на новый URL
                new_username = profile_form.cleaned_data.get("username")
                if new_username and new_username != username:
                    return redirect("members:edit_profile", username=new_username)
                return redirect("members:profile", username=request.user.username)

        elif "change_password" in request.POST:
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                messages.success(request, "Пароль успешно изменен!")
                # Перелогиниваем пользователя с новым паролем
                from django.contrib.auth import update_session_auth_hash

                update_session_auth_hash(request, request.user)
                return redirect("members:edit_profile", username=username)

    context = {
        "profile_user": profile_user,
        "profile_form": profile_form,
        "password_form": password_form,
    }
    return render(request, "users/profile_edit_member.html", context)


@login_required
def user_settings(request, username=None):
    """User settings page."""
    from django.utils import translation
    from django.conf import settings

    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            profile = form.save()
            
            # Активируем выбранный язык для текущей сессии
            language = profile.language
            translation.activate(language)
            # Сохраняем язык в сессии
            request.session['django_language'] = language
            # Принудительно сохраняем сессию
            request.session.modified = True
            
            messages.success(request, "Настройки сохранены!")
            # Перенаправляем на ту же страницу для применения изменений языка
            return redirect("members:settings", username=request.user.username)
    else:
        form = UserSettingsForm(instance=profile, user=request.user)

    return render(request, "users/settings.html", {"form": form})


@login_required
@require_http_methods(["POST"])
def subscribe(request, username):
    """Subscribe to a user."""
    channel = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    if request.user == channel:
        return JsonResponse({"error": "Cannot subscribe to yourself"}, status=400)

    subscription, created = Subscription.objects.get_or_create(
        subscriber=request.user, channel=channel
    )

    if created:
        # Update subscriber count
        channel.subscribers_count += 1
        channel.save(update_fields=["subscribers_count"])

        return JsonResponse(
            {"status": "subscribed", "subscribers_count": channel.subscribers_count}
        )
    else:
        return JsonResponse({"error": "Already subscribed"}, status=400)


@login_required
@require_http_methods(["POST"])
def unsubscribe(request, username):
    """Unsubscribe from a user."""
    channel = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    try:
        subscription = Subscription.objects.get(
            subscriber=request.user, channel=channel
        )
        subscription.delete()

        # Update subscriber count
        channel.subscribers_count = max(0, channel.subscribers_count - 1)
        channel.save(update_fields=["subscribers_count"])

        return JsonResponse(
            {"status": "unsubscribed", "subscribers_count": channel.subscribers_count}
        )
    except Subscription.DoesNotExist:
        return JsonResponse({"error": "Not subscribed"}, status=400)


@login_required
def subscriptions(request, username):
    """User's subscriptions."""
    from apps.users.models import User

    # Получаем пользователя по username
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )
    # Проверяем права доступа - только сам пользователь может видеть свои подписки
    if request.user != profile_user:
        messages.error(request, "У вас нет доступа к этому списку.")
        return redirect("members:profile", username=username)
    target_user = profile_user

    subscriptions = Subscription.objects.filter(subscriber=target_user).select_related(
        "channel"
    )

    # Get recent videos from subscribed channels
    subscribed_channels = [sub.channel for sub in subscriptions]
    recent_videos = (
        Video.objects.filter(created_by__in=subscribed_channels, status="published")
        .select_related("created_by", "category")
        .prefetch_related("tags")
        .order_by("-created_at")[:20]
    )

    context = {
        "subscriptions": subscriptions,
        "recent_videos": recent_videos,
        "profile_user": target_user,
    }
    return render(request, "users/subscriptions.html", context)


# Friendship Views
@login_required
@require_http_methods(["POST"])
def send_friend_request(request, username):
    """Отправить запрос в друзья."""
    to_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    if request.user == to_user:
        return JsonResponse(
            {"error": "Cannot send friend request to yourself"}, status=400
        )

    # Check if friendship already exists
    status, friendship = Friendship.get_friendship_status(request.user, to_user)

    if status:
        if status == "pending":
            return JsonResponse({"error": "Friend request already sent"}, status=400)
        elif status == "accepted":
            return JsonResponse({"error": "Already friends"}, status=400)
        elif status == "blocked":
            return JsonResponse({"error": "Cannot send friend request"}, status=400)

    # Create friendship request
    friendship = Friendship.objects.create(
        from_user=request.user, to_user=to_user, status="pending"
    )

    # Create notification
    Notification.create_friend_request_notification(request.user, to_user)

    return JsonResponse({"status": "sent", "message": "Friend request sent"})


@login_required
@require_http_methods(["POST"])
def accept_friend_request(request, username):
    """Принять запрос в друзья."""
    from_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    try:
        friendship = Friendship.objects.get(
            from_user=from_user, to_user=request.user, status="pending"
        )

        friendship.status = "accepted"
        friendship.save()

        # Create notification for sender
        Notification.create_friend_accepted_notification(from_user, request.user)

        return JsonResponse(
            {"status": "accepted", "message": "Friend request accepted"}
        )

    except Friendship.DoesNotExist:
        return JsonResponse({"error": "Friend request not found"}, status=404)


@login_required
@require_http_methods(["POST"])
def decline_friend_request(request, username):
    """Отклонить запрос в друзья."""
    from_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    try:
        friendship = Friendship.objects.get(
            from_user=from_user, to_user=request.user, status="pending"
        )

        friendship.status = "declined"
        friendship.save()

        return JsonResponse(
            {"status": "declined", "message": "Friend request declined"}
        )

    except Friendship.DoesNotExist:
        return JsonResponse({"error": "Friend request not found"}, status=404)


@login_required
@require_http_methods(["POST"])
def remove_friend(request, username):
    """Удалить из друзей."""
    friend_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    try:
        friendship = Friendship.objects.get(
            Q(from_user=request.user, to_user=friend_user)
            | Q(from_user=friend_user, to_user=request.user),
            status="accepted",
        )

        friendship.delete()

        return JsonResponse({"status": "removed", "message": "Friend removed"})

    except Friendship.DoesNotExist:
        return JsonResponse({"error": "Friendship not found"}, status=404)


# Notification Views
@login_required
def notifications(request, username):
    """Страница уведомлений."""
    from apps.users.models import User

    # Если username передан, используем его, иначе текущего пользователя
    if username:
        profile_user = get_object_or_404(
            User.objects.select_related("profile"), username=username
        )
        # Проверяем права доступа - только сам пользователь может видеть свои уведомления
        if request.user != profile_user:
            messages.error(request, "У вас нет доступа к этому списку.")
            return redirect("members:profile", username=username)
        target_user = profile_user
    else:
        target_user = request.user

    notifications = (
        Notification.objects.filter(recipient=target_user)
        .select_related("sender")
        .order_by("-created_at")
    )

    # Mark all as read
    notifications.filter(is_read=False).update(is_read=True)

    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "notifications": page_obj,
        "profile_user": target_user,
    }
    return render(request, "users/notifications.html", context)


# Password Reset Views
def password_reset_request(request):
    """Password reset request view."""
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                subject_template_name="users/password_reset_subject.txt",
                email_template_name="users/password_reset_email.html",
                from_email=None,
            )
            return redirect("users:password_reset_done")
    else:
        form = PasswordResetForm()

    return render(request, "users/password_reset.html", {"form": form})


def password_reset_done(request):
    """Password reset done view."""
    return render(request, "users/password_reset_done.html")


class PasswordResetConfirmViewCustom(PasswordResetConfirmView):
    """Custom password reset confirm view."""

    template_name = "users/password_reset_confirm.html"
    success_url = reverse_lazy("users:password_reset_complete")


def password_reset_confirm(request, uidb64, token):
    """Password reset confirm view."""
    view = PasswordResetConfirmViewCustom.as_view()
    return view(request, uidb64=uidb64, token=token)


def password_reset_complete(request):
    """Password reset complete view."""
    return render(request, "users/password_reset_complete.html")


@login_required
@require_http_methods(["GET"])
def notifications_count(request):
    """Получить количество непрочитанных уведомлений (HTMX)."""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, "users/htmx/notifications_count.html", {"count": count})


@login_required
@require_http_methods(["GET"])
def notifications_dropdown(request):
    """Получить последние уведомления для выпадающего списка (HTMX)."""
    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("sender")
        .order_by("-created_at")[:10]
    )
    return render(
        request,
        "users/htmx/notifications_dropdown.html",
        {"notifications": notifications},
    )


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Отметить уведомление как прочитанное."""
    try:
        notification = Notification.objects.get(
            id=notification_id, recipient=request.user
        )
        notification.mark_as_read()
        return JsonResponse({"status": "marked_read"})
    except Notification.DoesNotExist:
        return JsonResponse({"error": "Notification not found"}, status=404)


# Profile Tab Views
def profile_videos(request, username):
    """Profile videos tab."""
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    # Check privacy settings
    is_own_profile = request.user.is_authenticated and request.user == profile_user
    profile_obj = getattr(profile_user, 'profile', None)
    can_view = is_own_profile or (profile_obj and profile_obj.show_videos_publicly)

    page_obj = None
    if can_view:
        # Get user's videos
        videos = (
            Video.objects.filter(created_by=profile_user, status="published")
            .select_related("created_by", "category")
            .prefetch_related("tags")
            .order_by("-created_at")
        )

        # Pagination
        paginator = Paginator(videos, 12)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

    # Check subscription and friendship status
    is_subscribed = False
    friendship_status = None
    friendship_obj = None

    if request.user.is_authenticated and request.user != profile_user:
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user, channel=profile_user
        ).exists()
        friendship_status, friendship_obj = Friendship.get_friendship_status(
            request.user, profile_user
        )

    context = {
        "profile_user": profile_user,
        "page_obj": page_obj,
        "can_view_content": can_view,
        "is_subscribed": is_subscribed,
        "friendship_status": friendship_status,
        "friendship_obj": friendship_obj,
        "current_tab": "videos",
    }
    return render(request, "users/profile.html", context)


def profile_favorites(request, username):
    """Profile favorites tab."""
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    # Check privacy settings
    is_own_profile = request.user.is_authenticated and request.user == profile_user
    profile_obj = getattr(profile_user, 'profile', None)
    can_view = is_own_profile or (profile_obj and profile_obj.show_favorites_publicly)

    page_obj = None
    if can_view:
        from apps.videos.models import Favorite

        favorites = (
            Video.objects.filter(favorited_by__user=profile_user, status="published")
            .select_related("created_by", "category")
            .prefetch_related("tags")
            .order_by("-favorited_by__created_at")
        )

        # Pagination
        paginator = Paginator(favorites, 12)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

    # Check subscription and friendship status
    is_subscribed = False
    friendship_status = None
    friendship_obj = None

    if request.user.is_authenticated and request.user != profile_user:
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user, channel=profile_user
        ).exists()
        friendship_status, friendship_obj = Friendship.get_friendship_status(
            request.user, profile_user
        )

    context = {
        "profile_user": profile_user,
        "page_obj": page_obj,
        "can_view_content": can_view,
        "is_subscribed": is_subscribed,
        "friendship_status": friendship_status,
        "friendship_obj": friendship_obj,
        "current_tab": "favorites",
    }
    return render(request, "users/profile.html", context)


def profile_friends(request, username):
    """Profile friends tab."""
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    # Check privacy settings
    is_own_profile = request.user.is_authenticated and request.user == profile_user
    profile_obj = getattr(profile_user, 'profile', None)
    can_view = is_own_profile or (profile_obj and profile_obj.show_friends_publicly)

    page_obj = None
    friends_count = 0
    if can_view:
        # Get user's friends
        friends = Friendship.get_friends(profile_user)
        friends_count = friends.count()

        # Pagination
        paginator = Paginator(friends, 20)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

    # Check subscription and friendship status
    is_subscribed = False
    friendship_status = None
    friendship_obj = None

    if request.user.is_authenticated and request.user != profile_user:
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user, channel=profile_user
        ).exists()
        friendship_status, friendship_obj = Friendship.get_friendship_status(
            request.user, profile_user
        )

    context = {
        "profile_user": profile_user,
        "page_obj": page_obj,
        "friends_count": friends_count,
        "can_view_content": can_view,
        "is_subscribed": is_subscribed,
        "friendship_status": friendship_status,
        "friendship_obj": friendship_obj,
        "current_tab": "friends",
    }
    return render(request, "users/profile.html", context)


def profile_about(request, username):
    """Profile about tab."""
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    # Check subscription and friendship status
    is_subscribed = False
    friendship_status = None
    friendship_obj = None

    if request.user.is_authenticated and request.user != profile_user:
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user, channel=profile_user
        ).exists()
        friendship_status, friendship_obj = Friendship.get_friendship_status(
            request.user, profile_user
        )

    context = {
        "profile_user": profile_user,
        "is_subscribed": is_subscribed,
        "friendship_status": friendship_status,
        "friendship_obj": friendship_obj,
        "current_tab": "about",
    }
    return render(request, "users/profile.html", context)


def profile_subscriptions(request, username):
    """Profile subscriptions tab - only visible to profile owner."""
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    # Only profile owner can view subscriptions
    if not request.user.is_authenticated or request.user != profile_user:
        messages.error(request, "You do not have access to this page.")
        return redirect("members:profile", username=username)

    subscriptions = (
        Subscription.objects.filter(subscriber=profile_user)
        .select_related("channel", "channel__profile")
        .order_by("-created_at")
    )

    # Pagination
    paginator = Paginator(subscriptions, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "profile_user": profile_user,
        "page_obj": page_obj,
        "can_view_content": True,
        "current_tab": "subscriptions",
    }
    return render(request, "users/profile.html", context)


def profile_playlists(request, username):
    """Profile playlists tab - shows only public playlists to other users."""
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    is_own_profile = request.user.is_authenticated and request.user == profile_user

    # Get user's playlists
    from apps.videos.models import Playlist

    playlists = (
        Playlist.objects.filter(user=profile_user)
        .select_related("user")
        .prefetch_related("playlist_videos__video")
        .order_by("-created_at")
    )

    # Filter public playlists if not own profile
    if not is_own_profile:
        playlists = playlists.filter(privacy="public")

    # Pagination
    paginator = Paginator(playlists, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Check subscription and friendship status
    is_subscribed = False
    friendship_status = None
    friendship_obj = None

    if request.user.is_authenticated and request.user != profile_user:
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user, channel=profile_user
        ).exists()
        friendship_status, friendship_obj = Friendship.get_friendship_status(
            request.user, profile_user
        )

    context = {
        "profile_user": profile_user,
        "page_obj": page_obj,
        "can_view_content": True,
        "is_own_profile": is_own_profile,
        "is_subscribed": is_subscribed,
        "friendship_status": friendship_status,
        "friendship_obj": friendship_obj,
        "current_tab": "playlists",
    }
    return render(request, "users/profile.html", context)


def profile_watch_later(request, username):
    """Profile watch later tab."""
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    # Check privacy settings
    is_own_profile = request.user.is_authenticated and request.user == profile_user
    profile_obj = getattr(profile_user, 'profile', None)
    can_view = is_own_profile or (profile_obj and profile_obj.show_watch_later_publicly)

    page_obj = None
    if can_view:
        # Get watch later videos
        from apps.videos.models import WatchLater

        watch_later_videos = (
            Video.objects.filter(watch_later_entries__user=profile_user, status="published")
            .select_related("created_by", "category")
            .prefetch_related("tags")
            .order_by("-watch_later_entries__created_at")
        )

        # Pagination
        paginator = Paginator(watch_later_videos, 12)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

    # Check subscription and friendship status
    is_subscribed = False
    friendship_status = None
    friendship_obj = None

    if request.user.is_authenticated and request.user != profile_user:
        is_subscribed = Subscription.objects.filter(
            subscriber=request.user, channel=profile_user
        ).exists()
        friendship_status, friendship_obj = Friendship.get_friendship_status(
            request.user, profile_user
        )

    context = {
        "profile_user": profile_user,
        "page_obj": page_obj,
        "can_view_content": can_view,
        "is_subscribed": is_subscribed,
        "friendship_status": friendship_status,
        "friendship_obj": friendship_obj,
        "current_tab": "watch_later",
    }
    return render(request, "users/profile.html", context)


def profile_notifications(request, username):
    """Profile notifications tab - only visible to profile owner."""
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )

    # Only profile owner can view notifications
    if not request.user.is_authenticated or request.user != profile_user:
        messages.error(request, "You do not have access to this page.")
        return redirect("members:profile", username=username)

    # Get user's notifications
    user_notifications = (
        Notification.objects.filter(recipient=profile_user)
        .select_related("sender")
        .order_by("-created_at")
    )

    # Mark all as read when viewing
    user_notifications.filter(is_read=False).update(is_read=True)

    # Pagination
    paginator = Paginator(user_notifications, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "profile_user": profile_user,
        "page_obj": page_obj,
        "can_view_content": True,
        "current_tab": "notifications",
    }
    return render(request, "users/profile.html", context)
