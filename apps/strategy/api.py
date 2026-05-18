"""Strategy API.

Aggregates sub-routers from views/ for audience personas, competitor
analysis, content strategy, editorial calendar, OKR tracking,
and market research. All endpoints require Keycloak JWT authentication.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.strategy.views.calendar import router as calendar_router
from apps.strategy.views.competitors import router as competitors_router
from apps.strategy.views.okr import router as okr_router
from apps.strategy.views.personas import router as personas_router
from apps.strategy.views.research import router as research_router
from apps.strategy.views.strategy import router as strategy_router

router = Router(auth=VoyagerKeycloakBearer())

# Register all sub-routers
router.add_router("", personas_router)
router.add_router("", competitors_router)
router.add_router("", strategy_router)
router.add_router("", calendar_router)
router.add_router("", okr_router)
router.add_router("", research_router)


@router.get("/health", tags=["Strategy"])
def module_health(request) -> dict[str, str]:
    """Strategy module health check."""
    return {"status": "ok", "module": "strategy"}
