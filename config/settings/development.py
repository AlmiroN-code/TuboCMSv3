"""
Development settings for TubeCMS project.
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Development-specific apps
# Debug Toolbar removed

# Database for development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Development IPs (Debug Toolbar removed)
# INTERNAL_IPS = [
#     '127.0.0.1',
#     'localhost',
# ]

# Development-specific settings
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "gmpay.ru", "rextube.online", "*"]
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# File upload settings for development
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Cache for development (use local memory cache for testing)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "tubecms-dev-cache",
        "KEY_PREFIX": "tubecms_dev",
        "TIMEOUT": 300,
        "OPTIONS": {
            "MAX_ENTRIES": 500,
            "CULL_FREQUENCY": 3,
        },
    }
}

# Celery: eager режим для development без Redis
# Задачи выполняются синхронно в том же процессе
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# Simplified logging for development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
    },
}
