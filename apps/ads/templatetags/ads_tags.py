"""
Template tags for ads system.
"""
import random

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from ..models import AdBanner, AdPlacement, AdZone

register = template.Library()


@register.simple_tag
def ad_banner(placement_slug, request=None):
    """Display an ad banner for a specific placement."""
    from django.core.cache import cache

    # Use combined cache key for placement and banners
    cache_key = f"ad_placement_banners_{placement_slug}"
    cached_data = cache.get(cache_key)

    if cached_data is None:
        try:
            # Use optimized manager method
            banners = list(AdBanner.objects.get_for_placement_optimized(placement_slug))
            if banners:
                placement = banners[0].placement
                cached_data = {"placement": placement, "banners": banners}
            else:
                cached_data = False

            cache.set(cache_key, cached_data, 300)  # Cache for 5 minutes
        except:
            cache.set(cache_key, False, 300)  # Cache negative result
            return ""

    if cached_data is False:
        return ""

    placement = cached_data["placement"]
    banners = cached_data["banners"]

    if not banners:
        return ""

    # Weighted random selection
    total_weight = sum(banner.weight for banner in banners)
    if total_weight == 0:
        banner = random.choice(banners)
    else:
        random_num = random.randint(1, total_weight)
        current_weight = 0

        for banner in banners:
            current_weight += banner.weight
            if random_num <= current_weight:
                break
        else:
            banner = banners[0]

    # Record impression if request is available
    if request:
        banner.record_impression()

    context = {
        "banner": banner,
        "placement": placement,
    }

    return render_to_string("ads/banner.html", context)


@register.simple_tag
def ad_zone(zone_slug, request=None):
    """Display ads for a specific zone."""
    from django.core.cache import cache

    # Use combined cache key for zone and banners
    cache_key = f"ad_zone_complete_{zone_slug}"
    cached_data = cache.get(cache_key)

    if cached_data is None:
        try:
            # Use optimized manager method
            zone = AdZone.objects.active().with_placements().get(slug=zone_slug)

            # Get all banners for zone placements
            banners = []
            for placement in zone.placements.all():
                if placement.is_active:
                    placement_banners = list(
                        AdBanner.objects.get_for_placement_optimized(placement.slug)
                    )
                    banners.extend(placement_banners)

            cached_data = {"zone": zone, "banners": banners} if banners else False

            cache.set(cache_key, cached_data, 300)  # Cache for 5 minutes
        except AdZone.DoesNotExist:
            cache.set(cache_key, False, 300)  # Cache negative result
            return ""

    if cached_data is False:
        return ""

    zone = cached_data["zone"]
    cached_banners = cached_data["banners"]

    # Select banners from cached results
    banners = []
    if cached_banners:
        # Weighted random selection from cached banners
        total_weight = sum(banner.weight for banner in cached_banners)
        if total_weight == 0:
            banner = random.choice(cached_banners)
        else:
            random_num = random.randint(1, total_weight)
            current_weight = 0

            for banner in cached_banners:
                current_weight += banner.weight
                if random_num <= current_weight:
                    break
            else:
                banner = cached_banners[0]

        banners.append(banner)

        # Record impression if request is available
        if request:
            banner.record_impression()

    if not banners:
        return ""

    context = {
        "zone": zone,
        "banners": banners,
    }

    return render_to_string("ads/zone.html", context)


@register.simple_tag
def ad_placement_stats(placement_slug):
    """Get statistics for a specific placement."""
    try:
        placement = AdPlacement.objects.get(slug=placement_slug)
    except AdPlacement.DoesNotExist:
        return {}

    banners = AdBanner.objects.filter(placement=placement)

    stats = {
        "banners_count": banners.count(),
        "total_impressions": sum(banner.impressions_count for banner in banners),
        "total_clicks": sum(banner.clicks_count for banner in banners),
    }

    if stats["total_impressions"] > 0:
        stats["ctr"] = (stats["total_clicks"] / stats["total_impressions"]) * 100
    else:
        stats["ctr"] = 0

    return stats
