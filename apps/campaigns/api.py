"""
Campaigns API.

Endpoints for marketing campaign management — creation, execution,
tracking, and optimization across channels.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Campaigns"])
def module_health(request):
    """Campaigns module health check."""
    return {"status": "ok", "module": "campaigns"}
