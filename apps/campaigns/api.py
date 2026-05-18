"""Campaigns API router assembly.

Mounts all campaign management sub-routers under /campaigns.
"""

from __future__ import annotations

from ninja import Router

from apps.campaigns.views import (
    ab_testing_router,
    briefs_router,
    budget_router,
    channels_router,
    crud_router,
    lifecycle_router,
    performance_router,
)
from apps.rbac.auth import VoyagerKeycloakBearer

# Main campaigns router with auth
router = Router(auth=VoyagerKeycloakBearer())

# Mount sub-routers
router.add_router("/", crud_router, tags=["Campaigns"])
router.add_router("/lifecycle", lifecycle_router, tags=["Campaign Lifecycle"])
router.add_router("/budget", budget_router, tags=["Campaign Budget"])
router.add_router("/ab-tests", ab_testing_router, tags=["A/B Testing"])
router.add_router("/performance", performance_router, tags=["Campaign Performance"])
router.add_router("/channels", channels_router, tags=["Campaign Channels"])
router.add_router("/briefs", briefs_router, tags=["Campaign Briefs"])


@router.get("/health", tags=["Campaigns"])
def module_health(request) -> dict[str, str]:
    """Campaigns module health check.

    Returns:
        Health status dict.
    """
    return {"status": "ok", "module": "campaigns"}
