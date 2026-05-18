"""Connection CRUD endpoints."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from apps.integrations.api import router
from apps.integrations.api.helpers import (
    connection_detail_out,
    connection_out,
    get_tenant_id,
    get_user_id,
)
from apps.integrations.models import PlatformConnection
from apps.integrations.serializers import (
    ConnectionCreateIn,
    ConnectionOut,
    ConnectionUpdateIn,
)
from apps.integrations.services.oauth import revoke_connection


@router.get("/connections", response={200: dict}, tags=["Integrations"])
def list_connections(
    request: HttpRequest,
    platform: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """List platform connections for the current tenant."""
    tenant_id = get_tenant_id(request)
    qs = PlatformConnection.objects.filter(tenant_id=tenant_id)
    if platform:
        qs = qs.filter(platform=platform)
    if status:
        qs = qs.filter(status=status)
    total = qs.count()
    items = qs.order_by("-created_at")[offset : offset + limit]
    return {"items": [connection_out(c) for c in items], "total": total}


@router.post("/connections", response={200: ConnectionOut}, tags=["Integrations"])
def create_connection(request: HttpRequest, payload: ConnectionCreateIn) -> PlatformConnection:
    """Create a new platform connection (API-key or custom type)."""
    conn = PlatformConnection.objects.create(
        tenant_id=get_tenant_id(request),
        platform=payload.platform,
        connection_type=payload.connection_type,
        display_name=payload.display_name,
        scopes_json=payload.scopes_json,
        status=PlatformConnection.Status.PENDING,
        connected_by=get_user_id(request),
        metadata_json=payload.metadata_json,
    )
    if payload.api_key:
        conn.api_key = payload.api_key
        conn.status = PlatformConnection.Status.ACTIVE
        conn.save()
    return conn


@router.get("/connections/{connection_id}", response={200: dict}, tags=["Integrations"])
def get_connection(request: HttpRequest, connection_id: str) -> dict[str, Any]:
    """Get detailed information about a connection."""
    conn = get_object_or_404(PlatformConnection, id=connection_id, tenant_id=get_tenant_id(request))
    return connection_detail_out(conn)


@router.patch("/connections/{connection_id}", response={200: ConnectionOut}, tags=["Integrations"])
def update_connection(
    request: HttpRequest, connection_id: str, payload: ConnectionUpdateIn
) -> PlatformConnection:
    """Update a connection."""
    conn = get_object_or_404(PlatformConnection, id=connection_id, tenant_id=get_tenant_id(request))
    if payload.display_name is not None:
        conn.display_name = payload.display_name
    if payload.scopes_json is not None:
        conn.scopes_json = payload.scopes_json
    if payload.metadata_json is not None:
        conn.metadata_json = payload.metadata_json
    if payload.status is not None:
        conn.status = payload.status
    conn.save()
    return conn


@router.delete("/connections/{connection_id}", tags=["Integrations"])
def delete_connection(request: HttpRequest, connection_id: str) -> dict[str, bool]:
    """Delete a connection and all associated data."""
    conn = get_object_or_404(PlatformConnection, id=connection_id, tenant_id=get_tenant_id(request))
    conn.delete()
    return {"success": True}


@router.post("/connections/{connection_id}/revoke", tags=["Integrations"])
def revoke_conn(request: HttpRequest, connection_id: str) -> dict[str, Any]:
    """Revoke an OAuth connection and invalidate its tokens."""
    conn = get_object_or_404(PlatformConnection, id=connection_id, tenant_id=get_tenant_id(request))
    revoke_connection(conn)
    return {"success": True, "connection_id": connection_id, "status": conn.status}
