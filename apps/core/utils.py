"""
Utility functions for TubeCMS.
"""
import re

from django.utils.text import slugify


def generate_thumbnail_path(instance, filename):
    """Generate path for video thumbnail."""
    return f"thumbnails/{instance.user.id}/{filename}"


def generate_poster_path(instance, filename):
    """Generate path for video poster."""
    return f"posters/{instance.user.id}/{filename}"


def generate_video_path(instance, filename):
    """Generate path for video file."""
    return f"videos/{instance.user.id}/{filename}"


def clean_filename(filename):
    """Clean filename for safe storage."""
    # Remove special characters and replace with underscores
    filename = re.sub(r"[^\w\s-]", "", filename)
    # Replace spaces with underscores
    filename = re.sub(r"[-\s]+", "_", filename)
    return filename


def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"


def format_file_size(size_bytes):
    """Format file size in bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def get_site_settings():
    """Get active site settings with caching."""
    from .services import CacheService

    return CacheService.get_site_settings_cached()


def get_seo_settings():
    """Get active SEO settings with caching."""
    from .services import CacheService

    return CacheService.get_seo_settings_cached()
