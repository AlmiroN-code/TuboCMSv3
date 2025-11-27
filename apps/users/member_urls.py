"""
Member profile URL configuration for /members/username/ pattern.
"""

from django.urls import path

from apps.videos import views as video_views

from . import views

app_name = "members"

urlpatterns = [
    # Main profile page
    path("", views.profile, name="profile"),  # /members/username/
    # Profile tabs as separate URLs
    path("videos/", views.profile_videos, name="videos"),  # /members/username/videos/
    path(
        "favorites/", views.profile_favorites, name="favorites"
    ),  # /members/username/favorites/
    path(
        "friends/", views.profile_friends, name="friends"
    ),  # /members/username/friends/
    path("about/", views.profile_about, name="about"),  # /members/username/about/
    path(
        "subscriptions/", views.profile_subscriptions, name="subscriptions"
    ),  # /members/username/subscriptions/
    path(
        "playlists/", views.profile_playlists, name="playlists"
    ),  # /members/username/playlists/
    path(
        "watch-later/", views.profile_watch_later, name="watch_later"
    ),  # /members/username/watch-later/
    path(
        "notifications/", views.profile_notifications, name="notifications"
    ),  # /members/username/notifications/
    # Actions
    path(
        "subscribe/", views.subscribe, name="subscribe"
    ),  # /members/username/subscribe/
    path(
        "unsubscribe/", views.unsubscribe, name="unsubscribe"
    ),  # /members/username/unsubscribe/
    # Friendship URLs
    path(
        "add-friend/", views.send_friend_request, name="send_friend_request"
    ),  # /members/username/add-friend/
    path(
        "accept-friend/", views.accept_friend_request, name="accept_friend_request"
    ),  # /members/username/accept-friend/
    path(
        "decline-friend/", views.decline_friend_request, name="decline_friend_request"
    ),  # /members/username/decline-friend/
    path(
        "remove-friend/", views.remove_friend, name="remove_friend"
    ),  # /members/username/remove-friend/
    # Profile Edit
    path(
        "edit/", views.edit_profile_member, name="edit_profile"
    ),  # /members/username/edit/
    path(
        "settings/", views.user_settings, name="settings"
    ),  # /members/username/settings/
]
