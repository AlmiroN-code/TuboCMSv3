"""
Custom template tags for TubeCMS.
"""
from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()


@register.filter
def time_ago(value):
    """Return human readable time difference."""
    if not value:
        return ""
    
    now = timezone.now()
    diff = now - value
    
    if diff.days > 0:
        return f"{diff.days} дн. назад"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} ч. назад"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} мин. назад"
    else:
        return "только что"


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




