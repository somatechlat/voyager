"""
Analytics v2 API.

Endpoints for marketing analytics and reporting — dashboards,
attribution modeling, funnel analysis, custom reports.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Analytics"])
def module_health(request):
    """Analytics module health check."""
    return {"status": "ok", "module": "analytics_v2"}
