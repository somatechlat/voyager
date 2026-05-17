"""
Governance v2 API.

Endpoints for compliance and governance — approval workflows,
brand safety checks, regulatory compliance, data retention policies,
content moderation, access reviews.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Governance"])
def module_health(request):
    """Governance module health check."""
    return {"status": "ok", "module": "governance_v2"}
