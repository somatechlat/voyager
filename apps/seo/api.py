"""
SEO API.

Endpoints for search engine optimization — keyword research,
rank tracking, on-page analysis, backlink monitoring, technical SEO audits.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["SEO"])
def module_health(request):
    """SEO module health check."""
    return {"status": "ok", "module": "seo"}
