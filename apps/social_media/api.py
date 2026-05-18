"""Social Media API.

Endpoints for social media management — unified inbox, comment handling,
community management, hashtag research, influencer discovery,
social listening, and competitor benchmarking.

All routes are mounted under /api/v1/social/ via the core API router.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from .views.benchmarking import router as benchmarking_router
from .views.comments import router as comments_router
from .views.community import router as community_router
from .views.hashtags import router as hashtags_router
from .views.inbox import router as inbox_router
from .views.influencers import router as influencers_router
from .views.listening import router as listening_router

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Social Media"])
def module_health(request):
    """Social Media module health check."""
    return {"status": "ok", "module": "social_media"}


# Register sub-routers
router.add_router("/inbox", inbox_router, tags=["SM Inbox"])
router.add_router("/comments", comments_router, tags=["SM Comments"])
router.add_router("/community", community_router, tags=["SM Community"])
router.add_router("/hashtags", hashtags_router, tags=["SM Hashtags"])
router.add_router("/influencers", influencers_router, tags=["SM Influencers"])
router.add_router("/listening", listening_router, tags=["SM Listening"])
router.add_router("/benchmarking", benchmarking_router, tags=["SM Benchmarking"])
