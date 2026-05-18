"""Email Marketing API router assembly.

Mounts all email marketing sub-routers under /email-marketing.
"""

from __future__ import annotations

from ninja import Router

from apps.email_marketing.views import (
    ab_tests_router,
    analytics_router,
    automation_router,
    campaigns_router,
    deliverability_router,
    segments_router,
    subscribers_router,
    templates_router,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())

router.add_router("/templates", templates_router, tags=["Email Templates"])
router.add_router("/campaigns", campaigns_router, tags=["Email Campaigns"])
router.add_router("/automation", automation_router, tags=["Automation Sequences"])
router.add_router("/segments", segments_router, tags=["Audience Segments"])
router.add_router("/deliverability", deliverability_router, tags=["Deliverability"])
router.add_router("/ab-tests", ab_tests_router, tags=["A/B Testing"])
router.add_router("/analytics", analytics_router, tags=["Email Analytics"])
router.add_router("/subscribers", subscribers_router, tags=["Email Subscribers"])


@router.get("/health", tags=["Email Marketing"])
def module_health(request) -> dict[str, str]:
    """Email Marketing module health check.

    Returns:
        Health status dict.
    """
    return {"status": "ok", "module": "email_marketing"}
