"""
Pytest configuration for Django tests.
"""

import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import django
from django.conf import settings

# Configure Django settings for tests
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    django.setup()

# All tests in this directory will use django_db
import pytest

pytestmark = pytest.mark.django_db
