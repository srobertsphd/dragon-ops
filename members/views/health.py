"""
Health check view for deployment monitoring.
"""

from django.http import HttpResponse


def healthz(request):
    """Simple health check endpoint that returns 'ok'."""
    return HttpResponse("ok", content_type="text/plain")
