"""
URL configuration for ads app.
"""
from django.urls import path

from . import views

app_name = "ads"

urlpatterns = [
    # Ad display endpoints
    path("banner/<str:placement_slug>/", views.ad_banner_view, name="banner"),
    path("click/<int:banner_id>/", views.ad_click_view, name="click"),
    path("zone/<str:zone_slug>/", views.ad_zone_view, name="zone"),
    # Campaign management
    path("campaigns/", views.AdCampaignListView.as_view(), name="campaign_list"),
    path(
        "campaigns/<int:pk>/",
        views.AdCampaignDetailView.as_view(),
        name="campaign_detail",
    ),
    # Banner management
    path("banners/", views.AdBannerListView.as_view(), name="banner_list"),
    # API endpoints
    path("api/stats/", views.ad_stats_api, name="stats_api"),
    path(
        "api/placement/<str:placement_slug>/stats/",
        views.ad_placement_stats,
        name="placement_stats",
    ),
]
