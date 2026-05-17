"""
Content Creation API.

Endpoints for creating, editing, and managing marketing content —
blog posts, landing pages, ad copy, social posts, email templates.
"""

from __future__ import annotations

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/health", tags=["Content Creation"])
def module_health(request):
    """Content Creation module health check."""
    return {"status": "ok", "module": "content_creation"}
