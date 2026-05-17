"""
Publishing API.

Endpoints for scheduling and publishing content across channels —
CMS, social platforms, email delivery.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Publishing"])
def module_health(request):
    """Publishing module health check."""
    return {"status": "ok", "module": "publishing"}
