"""
URL Configuration for the Voyager Project.

Django architectural mandate: URL configs route ONLY.
View functions live in apps.core.views.py per Django conventions.

Operational endpoints:
    health / healthz    → Kubernetes liveness probe (lightweight)
    ready / readyz      → Kubernetes readiness probe (full dependency check)
    status              → Administrative status report
    version             → API version metadata
    api/v1/             → All application REST API routes (Django Ninja)
"""

from django.contrib import admin
from django.urls import include, path

from apps.core.api import api as v1_api
from apps.core.views import health, ready, status_view, version_view

# ==============================================================================
# URL Patterns
# ==============================================================================
# SECURITY WARNING: Operational endpoints expose internal state.
# Restrict access at the network/ingress level in production.
urlpatterns = [
    path("health", health),
    path("ready", ready),
    path("healthz", health),
    path("readyz", ready),
    path("status", status_view),
    path("version", version_view),
    path("api/v1/", v1_api.urls),
    path("admin/", admin.site.urls),
]
