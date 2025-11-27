"""
Language switching views for TubeCMS.
"""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.utils import translation
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect


@csrf_protect
@require_http_methods(["POST"])
def set_language(request):
    """
    Set user's language preference.
    For authenticated users, save to profile.
    For anonymous users, save to session only.
    """
    language = request.POST.get('language')
    next_url = request.POST.get('next', '/')
    
    # Validate language
    if language not in [lang[0] for lang in settings.LANGUAGES]:
        language = settings.LANGUAGE_CODE
    
    # Activate language for current request
    translation.activate(language)
    
    # Save to session
    request.session['django_language'] = language
    request.session.modified = True
    
    # For authenticated users, save to profile
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            profile.language = language
            profile.save(update_fields=['language'])
        except:
            # Profile doesn't exist, create it
            from apps.users.models import UserProfile
            UserProfile.objects.create(user=request.user, language=language)
    
    # Redirect back to the page
    response = HttpResponseRedirect(next_url)
    response.set_cookie(
        'django_language',
        language,
        max_age=settings.LANGUAGE_COOKIE_AGE,
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        secure=settings.LANGUAGE_COOKIE_SECURE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )
    
    return response