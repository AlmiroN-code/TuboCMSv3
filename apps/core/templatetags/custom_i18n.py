"""
Custom internationalization template tags.
"""

from django import template
from django.utils.safestring import mark_safe
from apps.core.translations import get_translation

register = template.Library()

@register.simple_tag(takes_context=True)
def trans_custom(context, text):
    """Custom translation tag that uses our manual translations."""
    request = context.get('request')
    
    # Get language from user profile or session
    language = 'en'  # default
    
    if request:
        # Try to get language from user profile
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                language = request.user.profile.language
            except:
                pass
        
        # Fallback to session language
        if not language or language == 'en':
            language = request.session.get('django_language', 'en')
    
    # Get translation
    translated = get_translation(text, language)
    return mark_safe(translated)