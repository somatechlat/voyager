"""API helper functions for serializing models to response dicts."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.integrations.models import (
    PlatformConnection,
    SyncLog,
    WebhookDelivery,
    WebhookEndpoint,
)


def get_tenant_id(request: HttpRequest) -> str:
    """Extract tenant ID from request headers."""
    return request.headers.get("X-Tenant-ID", "default")


def get_user_id(request: HttpRequest) -> str:
    """Extract user ID from request headers or auth."""
    user = getattr(request, "voyager_user", None)
    if user:
        return getattr(user, "user_id", "")
    return request.headers.get("X-User-ID", "")


def connection_out(conn: PlatformConnection) -> dict[str, Any]:
    """Serialize a PlatformConnection to ConnectionOut shape."""
    return {
        "id": str(conn.id),
        "tenant_id": conn.tenant_id,
        "platform": conn.platform,
        "platform_display": conn.get_platform_display(),
        "connection_type": conn.connection_type,
        "display_name": conn.display_name,
        "status": conn.status,
        "scopes_json": conn.scopes_list(),
        "expires_at": conn.expires_at,
        "last_refreshed_at": conn.last_refreshed_at,
        "last_error": conn.last_error,
        "created_at": conn.created_at,
        "updated_at": conn.updated_at,
    }


def connection_detail_out(conn: PlatformConnection) -> dict[str, Any]:
    """Serialize a PlatformConnection to ConnectionDetailOut shape."""
    detail = connection_out(conn)
    detail.update(
        {
            "token_type": conn.token_type,
            "metadata_json": conn.metadata_json,
            "connected_by": conn.connected_by,
            "is_expired": conn.is_expired(),
        }
    )
    return detail


def webhook_endpoint_out(endpoint: WebhookEndpoint) -> dict[str, Any]:
    """Serialize a WebhookEndpoint."""
    return {
        "id": str(endpoint.id),
        "connection_id": str(endpoint.connection_id),
        "name": endpoint.name,
        "event_type": endpoint.event_type,
        "endpoint_url": endpoint.endpoint_url,
        "is_active": endpoint.is_active,
        "status": endpoint.status,
        "last_triggered_at": endpoint.last_triggered_at,
        "created_at": endpoint.created_at,
    }


def webhook_delivery_out(delivery: WebhookDelivery) -> dict[str, Any]:
    """Serialize a WebhookDelivery."""
    return {
        "id": str(delivery.id),
        "webhook_id": str(delivery.webhook_id),
        "event_type": delivery.event_type,
        "status": delivery.status,
        "response_status": delivery.response_status,
        "attempt_count": delivery.attempt_count,
        "delivered_at": delivery.delivered_at,
        "created_at": delivery.created_at,
    }


def sync_log_out(log: SyncLog) -> dict[str, Any]:
    """Serialize a SyncLog."""
    return {
        "id": str(log.id),
        "connection_id": str(log.connection_id),
        "sync_type": log.sync_type,
        "direction": log.direction,
        "status": log.status,
        "records_count": log.records_count,
        "created_count": log.created_count,
        "updated_count": log.updated_count,
        "deleted_count": log.deleted_count,
        "conflict_count": log.conflict_count,
        "errors_json": log.errors_json,
        "started_at": log.started_at,
        "completed_at": log.completed_at,
        "duration_seconds": log.duration_seconds(),
        "created_at": log.created_at,
    }
