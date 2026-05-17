"""
Billing API.

Endpoints for billing and subscription management — invoicing,
plan management, usage tracking, payment processing, reporting.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Billing"])
def module_health(request):
    """Billing module health check."""
    return {"status": "ok", "module": "billing"}
