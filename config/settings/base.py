"""
Base settings for RexTube project.
"""

import os
from pathlib import Path

from celery.schedules import crontab
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-me-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition
DJANGO_APPS = [

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "django_extensions",
    "rosetta",
    "django_celery_beat",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.videos",
    "apps.comments",
    "apps.models",
    "apps.ads",
    "apps.localization",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Для статики
    "apps.core.middleware.PerformanceMiddleware",  # Мониторинг производительности
    "apps.core.middleware.CacheControlMiddleware",  # Управление кэшем
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # Локализация
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.UserLanguageMiddleware",  # Язык пользователя (ПОСЛЕ AuthenticationMiddleware)
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.CompressionMiddleware",  # Сжатие
    "apps.core.middleware.DatabaseOptimizationMiddleware",  # Мониторинг БД
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.theme",
                "apps.core.context_processors.categories",
                "apps.core.context_processors.global_settings",
                "apps.core.context_processors.language",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            "timeout": 20,  # Увеличиваем timeout для предотвращения блокировок
        },
    }
}

# Custom User Model
AUTH_USER_MODEL = "users.User"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
LANGUAGE_CODE = "en"  # Язык по умолчанию - английский
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# Supported languages
LANGUAGES = [
    ("en", "English"),
    ("ru", "Русский"),
]

# Path to locale files
LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery Configuration
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    # Video processing - every minute
    "videos_process_pending": {
        "task": "apps.videos.tasks.process_pending_videos",
        "schedule": 60.0,
        "args": (),
    },
    # Cleanup old drafts - daily at 03:00
    "videos_cleanup_old": {
        "task": "apps.videos.tasks.cleanup_old_videos",
        "schedule": crontab(minute=0, hour=3),
        "args": (),
    },
    # Alert system - every 5 minutes
    "check_alert_rules": {
        "task": "apps.videos.tasks.check_alert_rules",
        "schedule": 300.0,
        "args": (),
    },
    # Update video statistics - every hour
    "update_video_statistics": {
        "task": "apps.videos.tasks.update_video_statistics",
        "schedule": crontab(minute=0),
        "args": (),
    },
}

# Standard Django Admin Configuration
# Removed Django Unfold configuration for clean admin interface

# Enable Celery for async processing
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

# Celery Priority Queue Configuration
# Redis supports priority queues with different queue names
CELERY_TASK_ROUTES = {
    'apps.videos.tasks.process_video_async': {
        'queue': 'video_processing',
    },
}

# Define priority queues (higher number = higher priority)
CELERY_TASK_DEFAULT_PRIORITY = 5
CELERY_TASK_PRIORITY_LEVELS = {
    'critical': 10,  # Premium users, urgent tasks
    'high': 7,       # Premium users
    'normal': 5,     # Regular users
    'low': 3,        # New users
    'bulk': 1,       # Batch processing
}

# Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "tubecms-cache",
        "KEY_PREFIX": "tubecms",
        "TIMEOUT": 300,  # 5 minutes default
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
            "CULL_FREQUENCY": 3,
        },
    }
}

# Session Configuration
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 86400  # 24 hours

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "formatter": "verbose",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


