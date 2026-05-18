"""Publishing API.

Endpoints for scheduling and publishing content across channels --
CMS, social platforms, email delivery.

All routes are mounted under /api/v1/publishing/ via the core API router.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from .views.approval import router as approval_router
from .views.bulk import router as bulk_router
from .views.calendar import router as calendar_router
from .views.posts import router as posts_router
from .views.queue import router as queue_router
from .views.schedule import router as schedule_router

router = Router(auth=VoyagerKeycloakBearer())


# Health check
@router.get("/health", tags=["Publishing"])
def module_health(request):
    """Publishing module health check."""
    return {"status": "ok", "module": "publishing"}


# Register sub-routers
router.add_router("/posts", posts_router, tags=["Publishing Posts"])
router.add_router("/calendar", calendar_router, tags=["Publishing Calendar"])
router.add_router("/queue", queue_router, tags=["Publishing Queue"])
router.add_router("/schedule", schedule_router, tags=["Publishing Schedule"])
router.add_router("/approvals", approval_router, tags=["Publishing Approval"])
router.add_router("/bulk", bulk_router, tags=["Publishing Bulk"])
