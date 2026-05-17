"""
Email Marketing API.

Endpoints for email campaign management — template design, list management,
send scheduling, A/B testing, deliverability tracking, bounce handling.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Email Marketing"])
def module_health(request):
    """Email Marketing module health check."""
    return {"status": "ok", "module": "email_marketing"}
