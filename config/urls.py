"""
RexTube URL Configuration
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("rosetta/", include("rosetta.urls")),
    path("", include("apps.core.urls")),
    path("users/", include("apps.users.urls")),
    path(
        "members/<str:username>/", include("apps.users.member_urls")
    ),  # New member profile URLs
    path("category/", include("apps.core.category_urls")),  # Category URLs
    path("videos/", include("apps.videos.urls")),
    path("comments/", include("apps.comments.urls")),
    path("models/", include("apps.models.urls")),
    path("ads/", include("apps.ads.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    import debug_toolbar

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
