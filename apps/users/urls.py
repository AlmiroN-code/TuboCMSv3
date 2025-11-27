"""
User URL configuration.
"""
from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("profile/<str:username>/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("settings/", views.user_settings, name="settings"),
    path("subscribe/<str:username>/", views.subscribe, name="subscribe"),
    path("unsubscribe/<str:username>/", views.unsubscribe, name="unsubscribe"),
    # Notifications (HTMX endpoints - остаются без username)
    path("notifications/count/", views.notifications_count, name="notifications_count"),
    path(
        "notifications/dropdown/",
        views.notifications_dropdown,
        name="notifications_dropdown",
    ),
    path(
        "notifications/<int:notification_id>/read/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    # Password reset
    path("password-reset/", views.password_reset_request, name="password_reset"),
    path("password-reset/done/", views.password_reset_done, name="password_reset_done"),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    path(
        "password-reset-complete/",
        views.password_reset_complete,
        name="password_reset_complete",
    ),
]
