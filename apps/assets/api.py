"""
Assets API.

Endpoints for digital asset management — images, videos, documents,
template libraries, brand assets, asset tagging and search.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Assets"])
def module_health(request):
    """Assets module health check."""
    return {"status": "ok", "module": "assets"}
