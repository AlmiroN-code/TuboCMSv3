"""
Context processors for core app
"""
from django.contrib.admin.models import LogEntry
from django.core.cache import cache


def admin_log_entries(request):
    """
    Add log_entries to context for admin templates
    """
    if request.path.startswith("/admin/"):
        # Возвращаем QuerySet без slice, чтобы Django мог применить фильтры
        return {
            "log_entries": LogEntry.objects.select_related("content_type", "user").all()
        }
    return {}


def theme(request):
    """Theme context processor"""
    return {"theme": "default"}


def categories(request):
    """Categories context processor with caching"""
    from .services import CacheService

    return {"categories": CacheService.get_categories_cached()}


def global_settings(request):
    """Combined global settings context processor with caching"""
    from .services import CacheService

    return {
        "site_settings": CacheService.get_site_settings_cached(),
        "seo_settings": CacheService.get_seo_settings_cached(),
    }

def language(request):
    """Language context processor"""
    from django.utils import translation
    
    current_language = translation.get_language()
    return {
        'LANGUAGE_CODE': current_language,
        'CURRENT_LANGUAGE': current_language,
    }