"""
Clients API.

Endpoints for client/account management — client profiles, contacts,
contract management, onboarding, account health scoring.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Clients"])
def module_health(request):
    """Clients module health check."""
    return {"status": "ok", "module": "clients"}
