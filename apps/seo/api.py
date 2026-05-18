"""SEO API.

Endpoints for search engine optimization including keyword research,
on-page auditing, backlink analysis, technical crawling,
content optimization, rank tracking, and SEO reporting.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

# Import all sub-routers from views
from apps.seo.views.backlinks import router as backlinks_router
from apps.seo.views.content import router as content_router
from apps.seo.views.keywords import router as keywords_router
from apps.seo.views.onpage import router as onpage_router
from apps.seo.views.rank import router as rank_router
from apps.seo.views.reports import router as reports_router
from apps.seo.views.technical import router as technical_router

# Main router
router = Router(auth=VoyagerKeycloakBearer())

# Register all sub-routers
router.add_router("/keywords", keywords_router, tags=["SEO Keywords"])
router.add_router("/audits/onpage", onpage_router, tags=["SEO On-Page"])
router.add_router("/backlinks", backlinks_router, tags=["SEO Backlinks"])
router.add_router("/crawls", technical_router, tags=["SEO Technical"])
router.add_router("/content", content_router, tags=["SEO Content"])
router.add_router("/rank-tracking", rank_router, tags=["SEO Rank Tracking"])
router.add_router("/reports", reports_router, tags=["SEO Reports"])


@router.get("/health", tags=["SEO"])
def module_health(request) -> dict[str, str]:
    """SEO module health check."""
    return {"status": "ok", "module": "seo"}
