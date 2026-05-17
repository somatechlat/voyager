"""
Integrations API.

Endpoints for third-party integrations — connectors, credentials,
webhook management, API key management, sync configuration.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Integrations"])
def module_health(request):
    """Integrations module health check."""
    return {"status": "ok", "module": "integrations"}
