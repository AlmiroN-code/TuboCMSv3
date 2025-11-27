"""
Production settings for TubeCMS.
Database: SQLite3
"""
import os

from decouple import Csv, config

from .base import *

# Production settings
DEBUG = config("DEBUG", default=False, cast=bool)
SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="rextube.online,www.rextube.online", cast=Csv()
)

# Database - SQLite3 for production
# Using SQLite with WAL mode for better concurrency
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / config("DB_NAME", default="db.sqlite3"),
        "OPTIONS": {
            "timeout": 30,  # Increased timeout for concurrent access
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA cache_size=-64000;",
        },
    }
}

# Redis Cache configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/1"),
        "KEY_PREFIX": "rextube",
    }
}

# Session configuration - use Redis
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400 * 7  # 7 days

# Celery Configuration for Production
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Celery task settings
CELERY_TASK_ALWAYS_EAGER = False  # IMPORTANT: Must be False for async processing
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600  # 1 hour max per task
CELERY_TASK_SOFT_TIME_LIMIT = 3300  # Soft limit 55 minutes
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Process one task at a time for video encoding
CELERY_WORKER_CONCURRENCY = 2  # 2 concurrent workers

# Celery task routes
CELERY_TASK_ROUTES = {
    'apps.videos.tasks.process_video_async': {
        'queue': 'video_processing',
    },
    'apps.videos.tasks.check_alert_rules': {
        'queue': 'celery',
    },
}

# Celery Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Video processing - every minute
    'videos_process_pending': {
        'task': 'apps.videos.tasks.process_pending_videos',
        'schedule': 60.0,
        'args': (),
    },
    # Cleanup old drafts - daily at 03:00
    'videos_cleanup_old': {
        'task': 'apps.videos.tasks.cleanup_old_videos',
        'schedule': crontab(minute=0, hour=3),
        'args': (),
    },
    # Alert system - every 5 minutes
    'check_alert_rules': {
        'task': 'apps.videos.tasks.check_alert_rules',
        'schedule': 300.0,
        'args': (),
    },
    # Update video statistics - every hour
    'update_video_statistics': {
        'task': 'apps.videos.tasks.update_video_statistics',
        'schedule': crontab(minute=0),  # Every hour at :00
        'args': (),
    },
}

# Email configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@rextube.online")

# Static and media files
STATIC_ROOT = config("STATIC_ROOT", default=os.path.join(BASE_DIR, "staticfiles"))
MEDIA_ROOT = config("MEDIA_ROOT", default=os.path.join(BASE_DIR, "media"))

# WhiteNoise for static files
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

# File upload settings for video
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Logging configuration
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": config("LOG_FILE", default=os.path.join(LOG_DIR, "django.log")),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "celery_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "celery.log"),
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["file", "console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["celery_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.videos": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.videos.services": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Video processing settings
VIDEO_PROCESSING = {
    "MAX_UPLOAD_SIZE_MB": 500,
    "ALLOWED_EXTENSIONS": ["mp4", "avi", "mov", "wmv", "mkv", "webm"],
    "ENCODING_PROFILES": ["360p", "480p", "720p", "1080p"],
    "GENERATE_HLS": True,
    "GENERATE_DASH": True,
    "POSTER_WIDTH": 640,
    "POSTER_HEIGHT": 360,
    "PREVIEW_DURATION": 12,
}
