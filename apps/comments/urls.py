"""
Comment URL configuration.
"""
from django.urls import path

from . import views
from .htmx import views as htmx_views

app_name = "comments"

urlpatterns = [
    # Main views
    path("add/<slug:video_slug>/", views.add_comment, name="add"),
    path("edit/<int:comment_id>/", views.edit_comment, name="edit"),
    path("delete/<int:comment_id>/", views.delete_comment, name="delete"),
    path("like/<int:comment_id>/", views.like_comment, name="like"),
    path("report/<int:comment_id>/", views.report_comment, name="report"),
    path("get/<slug:video_slug>/", views.get_comments, name="get"),
    path("replies/<int:comment_id>/", views.get_replies, name="replies"),
    # HTMX views
    path("htmx/form/<slug:video_slug>/", htmx_views.comment_form, name="htmx_form"),
    path(
        "htmx/form/<slug:video_slug>/<int:parent_id>/",
        htmx_views.comment_form,
        name="htmx_reply_form",
    ),
    path(
        "htmx/create/<slug:video_slug>/", htmx_views.comment_create, name="htmx_create"
    ),
    path(
        "htmx/create/<slug:video_slug>/<int:parent_id>/",
        htmx_views.comment_create,
        name="htmx_reply_create",
    ),
    path(
        "htmx/edit-form/<int:comment_id>/",
        htmx_views.comment_edit_form,
        name="htmx_edit_form",
    ),
    path(
        "htmx/replies/<int:comment_id>/",
        htmx_views.comment_replies,
        name="htmx_replies",
    ),
    path(
        "htmx/report-form/<int:comment_id>/",
        htmx_views.comment_report_form,
        name="htmx_report_form",
    ),
    path("htmx/likes/<int:comment_id>/", htmx_views.comment_likes, name="htmx_likes"),
]
