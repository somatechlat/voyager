"""
Web Scraping v2 API.

Endpoints for web scraping and data collection — site crawling,
content extraction, competitor monitoring, SERP tracking.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Web Scraping"])
def module_health(request):
    """Web Scraping module health check."""
    return {"status": "ok", "module": "web_scraping_v2"}
