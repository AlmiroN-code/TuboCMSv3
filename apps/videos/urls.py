"""
Video URL configuration.
"""
from django.urls import path

from . import rating_views, views, views_progress
from .htmx import views as htmx_views

app_name = "videos"

urlpatterns = [
    # Main views
    path("", views.video_list, name="list"),
    path("upload/", views.video_upload, name="upload"),
    path("my-videos/", views.my_videos, name="my_videos"),
    path("watch-later/", views.watch_later_list, name="watch_later"),
    path("<slug:slug>/", views.video_detail, name="detail"),
    path("<slug:slug>/edit/", views.video_edit, name="edit"),
    path("<slug:slug>/delete/", views.video_delete, name="delete"),
    path("<slug:slug>/like/", views.video_like, name="like"),
    path("<slug:slug>/report/", views.video_report, name="report"),
    # HTMX views
    path("htmx/list/", htmx_views.video_list_partial, name="htmx_list"),
    path("htmx/<slug:slug>/like/", htmx_views.video_like_htmx, name="htmx_like"),
    path("htmx/<slug:slug>/actions/", htmx_views.video_actions, name="htmx_actions"),
    path("htmx/<slug:slug>/progress/", htmx_views.video_progress, name="htmx_progress"),
    path(
        "htmx/<slug:slug>/recommendations/",
        htmx_views.video_recommendations,
        name="htmx_recommendations",
    ),
    path(
        "htmx/<slug:slug>/watch-later/",
        htmx_views.watch_later_toggle,
        name="htmx_watch_later",
    ),
    path(
        "htmx/<slug:slug>/watch-later/button/",
        htmx_views.watch_later_button,
        name="htmx_watch_later_button",
    ),
    path(
        "htmx/<slug:slug>/favorite/", htmx_views.favorite_toggle, name="htmx_favorite"
    ),
    path(
        "htmx/<slug:slug>/favorite/button/",
        htmx_views.favorite_button,
        name="htmx_favorite_button",
    ),
    path(
        "htmx/<slug:slug>/playlist/button/",
        htmx_views.playlist_button,
        name="htmx_playlist_button",
    ),
    path(
        "htmx/upload-progress/<int:video_id>/",
        htmx_views.video_upload_progress,
        name="htmx_upload_progress",
    ),
    # Processing progress API
    path(
        "api/progress/<int:video_id>/",
        views_progress.video_processing_progress,
        name="api_progress",
    ),
    path(
        "api/retry/<int:video_id>/",
        views_progress.retry_video_processing,
        name="api_retry",
    ),
    # Rating views
    path("htmx/<slug:slug>/rating/", rating_views.video_rating, name="htmx_rating"),
    path(
        "htmx/<slug:slug>/rating/widget/",
        rating_views.video_rating_widget,
        name="htmx_rating_widget",
    ),
    # Favorites and Playlists
    path("<int:video_id>/add-favorite/", views.add_to_favorites, name="add_favorite"),
    path(
        "<int:video_id>/remove-favorite/",
        views.remove_from_favorites,
        name="remove_favorite",
    ),
    # Playlists
    path("playlists/", views.playlists_list, name="playlists_list"),
    path("playlists/create/", views.playlist_create, name="playlist_create"),
    path("playlists/<int:playlist_id>/", views.playlist_detail, name="playlist_detail"),
    path(
        "playlists/<int:playlist_id>/edit/", views.playlist_edit, name="playlist_edit"
    ),
    path(
        "playlists/<int:playlist_id>/delete/",
        views.playlist_delete,
        name="playlist_delete",
    ),
    path(
        "playlists/<int:playlist_id>/like/", views.playlist_like, name="playlist_like"
    ),
    path(
        "playlists/<int:playlist_id>/follow/",
        views.playlist_follow,
        name="playlist_follow",
    ),
    path("playlists/public/", views.public_playlists, name="public_playlists"),
    # Playlist video management
    path(
        "<int:video_id>/add-to-playlist/", views.add_to_playlist, name="add_to_playlist"
    ),
    path(
        "playlists/<int:playlist_id>/remove/<int:video_id>/",
        views.remove_from_playlist,
        name="remove_from_playlist",
    ),
    path(
        "htmx/<int:video_id>/playlists-modal/",
        views.user_playlists_modal,
        name="htmx_playlists_modal",
    ),
]
