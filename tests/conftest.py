"""
Pytest configuration for Django tests.

This file ensures Django is configured before any Django imports happen.
"""

import os
import django
from django.conf import settings

# Configure Django settings before any Django imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alano_club_site.settings")

# Configure Django if not already configured
if not settings.configured:
    django.setup()

    # Override static files storage for tests to avoid manifest issues
    settings.STATICFILES_STORAGE = (
        "django.contrib.staticfiles.storage.StaticFilesStorage"
    )
