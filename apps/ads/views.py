"""
Views for ads system.
"""
import json
import random

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView

from .models import AdBanner, AdCampaign, AdClick, AdImpression, AdPlacement, AdZone


def get_banner_for_placement(placement_slug, request=None):
    """Get a random banner for a specific placement."""
    try:
        placement = AdPlacement.objects.get(slug=placement_slug, is_active=True)
    except AdPlacement.DoesNotExist:
        return None

    # Get active banners for this placement
    banners = AdBanner.objects.filter(
        placement=placement,
        is_active=True,
        campaign__status="active",
        campaign__is_active=True,
    ).select_related("campaign", "placement")

    if not banners:
        return None

    # Weighted random selection
    total_weight = sum(banner.weight for banner in banners)
    if total_weight == 0:
        return random.choice(banners)

    random_num = random.randint(1, total_weight)
    current_weight = 0

    for banner in banners:
        current_weight += banner.weight
        if random_num <= current_weight:
            return banner

    return banners.first()


def record_impression(banner, request):
    """Record an ad impression."""
    if not banner:
        return

    # Record impression in banner
    banner.record_impression()

    # Record detailed impression
    AdImpression.objects.create(
        banner=banner,
        ip_address=request.META.get("REMOTE_ADDR", ""),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        referer=request.META.get("HTTP_REFERER", ""),
    )


def record_click(banner, request):
    """Record an ad click."""
    if not banner:
        return

    # Record click in banner
    banner.record_click()

    # Record detailed click
    AdClick.objects.create(
        banner=banner,
        ip_address=request.META.get("REMOTE_ADDR", ""),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        referer=request.META.get("HTTP_REFERER", ""),
    )


@require_http_methods(["GET"])
def ad_banner_view(request, placement_slug):
    """Display an ad banner."""
    banner = get_banner_for_placement(placement_slug, request)

    if not banner:
        return HttpResponse("")

    # Record impression
    record_impression(banner, request)

    context = {
        "banner": banner,
        "placement": banner.placement,
    }

    return render(request, "ads/banner.html", context)


@require_http_methods(["GET"])
def ad_click_view(request, banner_id):
    """Handle ad click and redirect."""
    banner = get_object_or_404(AdBanner, id=banner_id, is_active=True)

    # Record click
    record_click(banner, request)

    # Redirect to target URL
    return redirect(banner.target_url)


@require_http_methods(["GET"])
def ad_zone_view(request, zone_slug):
    """Display ads for a specific zone."""
    try:
        zone = AdZone.objects.get(slug=zone_slug, is_active=True)
    except AdZone.DoesNotExist:
        return HttpResponse("")

    banners = []
    for placement in zone.placements.filter(is_active=True):
        banner = get_banner_for_placement(placement.slug, request)
        if banner:
            banners.append(banner)
            record_impression(banner, request)

    context = {
        "zone": zone,
        "banners": banners,
    }

    return render(request, "ads/zone.html", context)


class AdCampaignListView(LoginRequiredMixin, ListView):
    """List view for ad campaigns."""

    model = AdCampaign
    template_name = "ads/campaign_list.html"
    context_object_name = "campaigns"
    paginate_by = 20

    def get_queryset(self):
        return AdCampaign.objects.filter(advertiser=self.request.user).order_by(
            "-created_at"
        )


class AdCampaignDetailView(LoginRequiredMixin, DetailView):
    """Detail view for ad campaign."""

    model = AdCampaign
    template_name = "ads/campaign_detail.html"
    context_object_name = "campaign"

    def get_queryset(self):
        return AdCampaign.objects.filter(advertiser=self.request.user)


class AdBannerListView(LoginRequiredMixin, ListView):
    """List view for ad banners."""

    model = AdBanner
    template_name = "ads/banner_list.html"
    context_object_name = "banners"
    paginate_by = 20

    def get_queryset(self):
        return (
            AdBanner.objects.filter(campaign__advertiser=self.request.user)
            .select_related("campaign", "placement")
            .order_by("-created_at")
        )


@require_http_methods(["GET"])
def ad_stats_api(request):
    """API endpoint for ad statistics."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)

    # Get user's campaigns
    campaigns = AdCampaign.objects.filter(advertiser=request.user)

    stats = {
        "total_campaigns": campaigns.count(),
        "active_campaigns": campaigns.filter(status="active").count(),
        "total_banners": AdBanner.objects.filter(campaign__in=campaigns).count(),
        "total_impressions": AdImpression.objects.filter(
            banner__campaign__in=campaigns
        ).count(),
        "total_clicks": AdClick.objects.filter(banner__campaign__in=campaigns).count(),
    }

    # Calculate overall CTR
    if stats["total_impressions"] > 0:
        stats["overall_ctr"] = (
            stats["total_clicks"] / stats["total_impressions"]
        ) * 100
    else:
        stats["overall_ctr"] = 0

    return JsonResponse(stats)


@require_http_methods(["GET"])
def ad_placement_stats(request, placement_slug):
    """Get statistics for a specific placement."""
    try:
        placement = AdPlacement.objects.get(slug=placement_slug)
    except AdPlacement.DoesNotExist:
        return JsonResponse({"error": "Placement not found"}, status=404)

    banners = AdBanner.objects.filter(placement=placement)

    stats = {
        "placement": {
            "name": placement.name,
            "type": placement.placement_type,
            "size": f"{placement.width}x{placement.height}",
        },
        "banners_count": banners.count(),
        "total_impressions": sum(banner.impressions_count for banner in banners),
        "total_clicks": sum(banner.clicks_count for banner in banners),
    }

    if stats["total_impressions"] > 0:
        stats["overall_ctr"] = (
            stats["total_clicks"] / stats["total_impressions"]
        ) * 100
    else:
        stats["overall_ctr"] = 0

    return JsonResponse(stats)
