"""
Custom template tags for TubeCMS.
"""
from datetime import timedelta

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def time_ago(value):
    """Return human readable time difference in English."""
    if not value:
        return ""

    now = timezone.now()
    diff = now - value

    total_seconds = int(diff.total_seconds())

    # Years
    if total_seconds >= 31536000:  # 365 days
        years = total_seconds // 31536000
        return f"{years} year{'s' if years != 1 else ''} ago"

    # Months (approximate, 30 days)
    if total_seconds >= 2592000:  # 30 days
        months = total_seconds // 2592000
        return f"{months} month{'s' if months != 1 else ''} ago"

    # Weeks
    if total_seconds >= 604800:  # 7 days
        weeks = total_seconds // 604800
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    # Days
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"

    # Hours
    if total_seconds >= 3600:
        hours = total_seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    # Minutes
    if total_seconds >= 60:
        minutes = total_seconds // 60
        return f"{minutes} min. ago"

    # Seconds
    if total_seconds > 0:
        return f"{total_seconds} second{'s' if total_seconds != 1 else ''} ago"

    # Just now
    return "just now"


@register.filter
def format_views(value):
    """Format view count."""
    if value >= 1000000:
        return f"{value/1000000:.1f}M"
    elif value >= 1000:
        return f"{value/1000:.1f}K"
    else:
        return str(value)


@register.filter
def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS format."""
    if not seconds:
        return "0:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"


@register.filter
def truncate_text(text, length=100):
    """Truncate text to specified length."""
    if len(text) <= length:
        return text
    return text[:length] + "..."


@register.simple_tag
def get_avatar_initial(user):
    """Get first letter of username for avatar."""
    if user.first_name:
        return user.first_name[0].upper()
    elif user.username:
        return user.username[0].upper()
    return "U"


@register.simple_tag
def get_site_setting(setting_name):
    """Get a specific site setting value."""
    from ..utils import get_site_settings

    settings = get_site_settings()
    if settings:
        return getattr(settings, setting_name, "")
    return ""


@register.simple_tag
def get_seo_setting(setting_name):
    """Get a specific SEO setting value."""
    from ..utils import get_seo_settings

    settings = get_seo_settings()
    if settings:
        return getattr(settings, setting_name, "")
    return ""


@register.inclusion_tag("core/social_links.html")
def social_links():
    """Render social media links."""
    from ..utils import get_site_settings

    settings = get_site_settings()
    if settings:
        return {
            "social_vk": settings.social_vk,
            "social_telegram": settings.social_telegram,
            "social_youtube": settings.social_youtube,
            "social_twitter": settings.social_twitter,
            "social_instagram": settings.social_instagram,
        }
    return {}


@register.simple_tag(takes_context=True)
def absolute_url(context, url):
    """Build absolute URL from relative URL."""
    request = context["request"]
    return request.build_absolute_uri(url)


@register.simple_tag
def url_replace(request, field, value):
    """
    Replace or add a parameter in the current URL query string.
    Usage: {% url_replace request 'page' 2 %}
    """
    query_dict = request.GET.copy()
    query_dict[field] = value
    return query_dict.urlencode()


@register.simple_tag
def current_language():
    """Get current language code."""
    from django.utils import translation
    return translation.get_language()