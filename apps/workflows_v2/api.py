"""
Workflows v2 API.

Endpoints for workflow automation — workflow design (Vortex integration),
execution tracking, template management, approval chains, scheduling.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Workflows"])
def module_health(request):
    """Workflows module health check."""
    return {"status": "ok", "module": "workflows_v2"}
