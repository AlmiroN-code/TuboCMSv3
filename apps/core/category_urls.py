"""
Category URL configuration for /category/slug/ pattern.
"""
from django.urls import path

from apps.videos import views as video_views

app_name = "category"

urlpatterns = [
    path("<slug:slug>/", video_views.category_videos, name="videos"),  # /category/slug/
]
