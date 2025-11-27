"""
Performance optimization middleware.
"""
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class PerformanceMiddleware(MiddlewareMixin):
    """Middleware for performance monitoring and optimization."""

    def process_request(self, request):
        """Start timing the request."""
        request._start_time = time.time()
        return None

    def process_response(self, request, response):
        """Log slow requests and add performance headers."""
        if hasattr(request, "_start_time"):
            duration = time.time() - request._start_time

            # Log slow requests (> 1 second)
            if duration > 1.0:
                logger.warning(
                    f"Slow request: {request.method} {request.path} took {duration:.2f}s"
                )

            # Add performance header in debug mode
            if settings.DEBUG:
                response["X-Response-Time"] = f"{duration:.3f}s"

        return response


class CacheControlMiddleware(MiddlewareMixin):
    """Middleware for setting cache control headers."""

    # Paths that should be cached by browser
    CACHEABLE_PATHS = [
        "/static/",
        "/media/",
    ]

    # Paths that should never be cached
    NO_CACHE_PATHS = [
        "/admin/",
        "/api/",
    ]

    def process_response(self, request, response):
        """Set appropriate cache headers."""
        path = request.path

        # Static files - long cache
        if any(path.startswith(cacheable) for cacheable in self.CACHEABLE_PATHS):
            response["Cache-Control"] = "public, max-age=31536000"  # 1 year
            return response

        # Admin and API - no cache
        if any(path.startswith(no_cache) for no_cache in self.NO_CACHE_PATHS):
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
            return response

        # Default - short cache for public pages
        if hasattr(request, 'user') and request.user.is_anonymous and request.method == "GET":
            response["Cache-Control"] = "public, max-age=300"  # 5 minutes
        else:
            response["Cache-Control"] = "private, max-age=0"

        return response


class CompressionMiddleware(MiddlewareMixin):
    """Middleware for response compression hints."""

    def process_response(self, request, response):
        """Add compression hints."""
        # Suggest compression for text content
        content_type = response.get("Content-Type", "")
        if any(
            ct in content_type
            for ct in ["text/", "application/json", "application/javascript"]
        ):
            response["Vary"] = "Accept-Encoding"

        return response


class DatabaseOptimizationMiddleware(MiddlewareMixin):
    """Middleware for database query optimization monitoring."""

    def process_request(self, request):
        """Reset query count."""
        if settings.DEBUG:
            from django.db import reset_queries

            reset_queries()
        return None

    def process_response(self, request, response):
        """Log database queries in debug mode."""
        if settings.DEBUG:
            from django.db import connection

            queries = connection.queries

            if len(queries) > 10:  # Warn about too many queries
                logger.warning(
                    f"High query count: {request.method} {request.path} "
                    f"executed {len(queries)} database queries"
                )

                # Log slow queries
                slow_queries = [q for q in queries if float(q["time"]) > 0.1]
                if slow_queries:
                    logger.warning(
                        f"Slow queries detected: {len(slow_queries)} queries > 0.1s"
                    )

        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Simple rate limiting middleware."""

    def process_request(self, request):
        """Check rate limits for anonymous users."""
        if request.user.is_anonymous:
            ip = self.get_client_ip(request)
            cache_key = f"rate_limit_{ip}"

            # Get current request count
            current_requests = cache.get(cache_key, 0)

            # Allow 100 requests per minute for anonymous users
            if current_requests >= 100:
                return HttpResponse(
                    "Rate limit exceeded. Please try again later.", status=429
                )

            # Increment counter
            cache.set(cache_key, current_requests + 1, 60)  # 1 minute window

        return None

    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip



class UserLanguageMiddleware(MiddlewareMixin):
    """Middleware for setting user's preferred language."""

    def process_request(self, request):
        """Set language based on user profile."""
        from django.utils import translation

        # Проверяем, что пользователь существует и аутентифицирован
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                profile = request.user.profile
                language = profile.language
                
                # Активируем язык пользователя
                translation.activate(language)
                request.LANGUAGE_CODE = language
                
                # Сохраняем язык в сессии для Django LocaleMiddleware
                request.session['django_language'] = language
            except Exception:
                # Если профиль не существует, используем язык по умолчанию
                pass

        return None
