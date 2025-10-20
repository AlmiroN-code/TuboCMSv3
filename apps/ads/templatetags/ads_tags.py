"""
Template tags for ads system.
"""
from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from ..models import AdPlacement, AdBanner, AdZone
import random

register = template.Library()


@register.simple_tag
def ad_banner(placement_slug, request=None):
    """Display an ad banner for a specific placement."""
    try:
        placement = AdPlacement.objects.get(slug=placement_slug, is_active=True)
    except AdPlacement.DoesNotExist:
        return ''
    
    # Get active banners for this placement
    banners = AdBanner.objects.filter(
        placement=placement,
        is_active=True,
        campaign__status='active',
        campaign__is_active=True
    ).select_related('campaign', 'placement')
    
    if not banners:
        return ''
    
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
            banner = banners.first()
    
    # Record impression if request is available
    if request:
        banner.record_impression()
    
    context = {
        'banner': banner,
        'placement': placement,
    }
    
    return render_to_string('ads/banner.html', context)


@register.simple_tag
def ad_zone(zone_slug, request=None):
    """Display ads for a specific zone."""
    try:
        zone = AdZone.objects.get(slug=zone_slug, is_active=True)
    except AdZone.DoesNotExist:
        return ''
    
    banners = []
    for placement in zone.placements.filter(is_active=True):
        banners_query = AdBanner.objects.filter(
            placement=placement,
            is_active=True,
            campaign__status='active',
            campaign__is_active=True
        ).select_related('campaign', 'placement')
        
        if banners_query.exists():
            # Weighted random selection
            total_weight = sum(banner.weight for banner in banners_query)
            if total_weight == 0:
                banner = random.choice(banners_query)
            else:
                random_num = random.randint(1, total_weight)
                current_weight = 0
                
                for banner in banners_query:
                    current_weight += banner.weight
                    if random_num <= current_weight:
                        break
                else:
                    banner = banners_query.first()
            
            banners.append(banner)
            
            # Record impression if request is available
            if request:
                banner.record_impression()
    
    if not banners:
        return ''
    
    context = {
        'zone': zone,
        'banners': banners,
    }
    
    return render_to_string('ads/zone.html', context)


@register.simple_tag
def ad_placement_stats(placement_slug):
    """Get statistics for a specific placement."""
    try:
        placement = AdPlacement.objects.get(slug=placement_slug)
    except AdPlacement.DoesNotExist:
        return {}
    
    banners = AdBanner.objects.filter(placement=placement)
    
    stats = {
        'banners_count': banners.count(),
        'total_impressions': sum(banner.impressions_count for banner in banners),
        'total_clicks': sum(banner.clicks_count for banner in banners),
    }
    
    if stats['total_impressions'] > 0:
        stats['ctr'] = (stats['total_clicks'] / stats['total_impressions']) * 100
    else:
        stats['ctr'] = 0
    
    return stats



