"""Views package for the Clients CRM module.

Composes all sub-routers into a single router for registration
in the main API.
"""

from __future__ import annotations

from ninja import Router

from apps.clients.views.clients import router as clients_router
from apps.clients.views.communications import router as comms_router
from apps.clients.views.portals import router as portals_router
from apps.clients.views.profitability import router as profit_router
from apps.clients.views.projects import router as projects_router

router = Router()


@router.get("/health", tags=["Clients"])
def module_health(request):
    """Clients module health check."""
    return {"status": "ok", "module": "clients"}


# Mount all sub-routers
router.add_router("", clients_router)
router.add_router("", projects_router)
router.add_router("", comms_router)
router.add_router("", portals_router)
router.add_router("", profit_router)
