"""
Video URL configuration.
"""
from django.urls import path
from . import views
from .htmx import views as htmx_views

app_name = 'videos'

urlpatterns = [
    # Main views
    path('', views.video_list, name='list'),
    path('upload/', views.video_upload, name='upload'),
    path('my-videos/', views.my_videos, name='my_videos'),
    path('<slug:slug>/', views.video_detail, name='detail'),
    path('<slug:slug>/edit/', views.video_edit, name='edit'),
    path('<slug:slug>/delete/', views.video_delete, name='delete'),
    path('<slug:slug>/like/', views.video_like, name='like'),
    path('<slug:slug>/report/', views.video_report, name='report'),
    path('category/<slug:slug>/', views.category_videos, name='category'),
    
    # HTMX views
    path('htmx/list/', htmx_views.video_list_partial, name='htmx_list'),
    path('htmx/<slug:slug>/like/', htmx_views.video_like_htmx, name='htmx_like'),
    path('htmx/<slug:slug>/actions/', htmx_views.video_actions, name='htmx_actions'),
    path('htmx/<slug:slug>/progress/', htmx_views.video_progress, name='htmx_progress'),
    path('htmx/<slug:slug>/recommendations/', htmx_views.video_recommendations, name='htmx_recommendations'),
    path('htmx/search-suggestions/', htmx_views.video_search_suggestions, name='htmx_search_suggestions'),
    path('htmx/upload-progress/<int:video_id>/', htmx_views.video_upload_progress, name='htmx_upload_progress'),
]










