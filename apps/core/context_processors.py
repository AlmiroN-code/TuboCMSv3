from apps.core.models import Category


def theme(request):
    """Add theme to all templates."""
    # Get theme from user profile if authenticated
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        theme_preference = request.user.profile.theme_preference
    else:
        theme_preference = 'dark'  # Default theme
    
    return {
        'theme': theme_preference
    }


def categories(request):
    """Add categories to all templates."""
    return {
        'categories': Category.objects.filter(is_active=True).order_by('order', 'name')
    }