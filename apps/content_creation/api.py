"""Content Creation API.

Aggregates all sub-routers into a single router registered in api_main.py.

Sub-routers:
  - /content/generate      → text, image, video generation
  - /content/generations   → retrieve generation records
  - /content/brand-kits    → brand kit CRUD
  - /content/templates     → template CRUD + rendering
  - /content/ab-tests      → A/B test CRUD + winner
  - /content/revisions     → revision history
  - /content/repurposing   → content repurposing
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from .views.ab_tests import router as ab_tests_router
from .views.brand_kits import router as brand_kits_router
from .views.generation import router as generation_router
from .views.repurposing import router as repurposing_router
from .views.revisions import router as revisions_router
from .views.templates import router as templates_router

router = Router(auth=VoyagerKeycloakBearer())

# Register all sub-routers
router.add_router("", generation_router)
router.add_router("", brand_kits_router)
router.add_router("", templates_router)
router.add_router("", ab_tests_router)
router.add_router("", revisions_router)
router.add_router("", repurposing_router)


@router.get("/health", tags=["Content Creation"])
def module_health(request) -> dict[str, str]:
    """Content Creation module health check."""
    return {"status": "ok", "module": "content_creation"}
