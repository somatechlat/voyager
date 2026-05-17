"""
Team API.

Endpoints for team management — member profiles, workload tracking,
activity feeds, collaboration, permissions delegation.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Team"])
def module_health(request):
    """Team module health check."""
    return {"status": "ok", "module": "team"}
