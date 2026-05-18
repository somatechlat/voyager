"""OAuth flow endpoints."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from apps.integrations.api import router
from apps.integrations.api.helpers import get_tenant_id
from apps.integrations.models import PlatformConnection
from apps.integrations.serializers import OAuthCallbackIn
from apps.integrations.services.oauth import (
    handle_oauth_callback,
    initiate_oauth_flow,
    refresh_access_token,
)


@router.get("/{platform}/auth-url", response={200: dict}, tags=["Integrations"])
def get_auth_url(request: HttpRequest, platform: str, scopes: str = "") -> dict[str, str]:
    """Generate an OAuth authorization URL for a platform."""
    tenant_id = get_tenant_id(request)
    scope_list = scopes.split(",") if scopes else []
    return initiate_oauth_flow(tenant_id, platform, scope_list)


@router.post("/{platform}/callback", response={200: dict}, tags=["Integrations"])
def oauth_callback(request: HttpRequest, platform: str, payload: OAuthCallbackIn) -> dict[str, Any]:
    """Handle OAuth callback: exchange code for tokens."""
    result = handle_oauth_callback(payload.code, payload.state)
    result["success"] = True
    return result


@router.post("/connections/{connection_id}/refresh", tags=["Integrations"])
def refresh_token(request: HttpRequest, connection_id: str) -> dict[str, Any]:
    """Manually refresh the access token for a connection."""
    conn = get_object_or_404(PlatformConnection, id=connection_id, tenant_id=get_tenant_id(request))
    return refresh_access_token(conn)
