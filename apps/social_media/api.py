"""
Social Media API.

Endpoints for social media management — post creation, scheduling,
engagement tracking, analytics across platforms (Twitter, LinkedIn,
Facebook, Instagram, TikTok).
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Social Media"])
def module_health(request):
    """Social Media module health check."""
    return {"status": "ok", "module": "social_media"}
