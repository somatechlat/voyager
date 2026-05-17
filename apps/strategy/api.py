"""
Strategy API.

Endpoints for marketing strategy planning — goal setting,
audience segmentation, competitive analysis, budget allocation.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Strategy"])
def module_health(request):
    """Strategy module health check."""
    return {"status": "ok", "module": "strategy"}
