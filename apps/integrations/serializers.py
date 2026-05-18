"""Pydantic schemas for the Integrations Hub API.

Request/response models for connections, OAuth, webhooks, sync, and health.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Schema

# ---------------------------------------------------------------------------
# Connection schemas
# ---------------------------------------------------------------------------


class ConnectionCreateIn(Schema):
    """Request body for creating a new platform connection."""

    platform: str
    connection_type: str = "oauth"
    display_name: str = ""
    scopes_json: list[str] = []
    api_key: str = ""
    metadata_json: dict[str, Any] = {}


class ConnectionUpdateIn(Schema):
    """Request body for updating a connection."""

    display_name: str | None = None
    scopes_json: list[str] | None = None
    metadata_json: dict[str, Any] | None = None
    status: str | None = None


class ConnectionOut(Schema):
    """Response model for a platform connection."""

    id: str
    tenant_id: str
    platform: str
    platform_display: str
    connection_type: str
    display_name: str
    status: str
    scopes_json: list[str]
    expires_at: datetime | None
    last_refreshed_at: datetime | None
    last_error: str
    created_at: datetime
    updated_at: datetime


class ConnectionListOut(Schema):
    """Paginated list of connections."""

    items: list[ConnectionOut]
    total: int


class ConnectionDetailOut(ConnectionOut):
    """Detailed connection response."""

    token_type: str
    metadata_json: dict[str, Any]
    connected_by: str
    is_expired: bool


# ---------------------------------------------------------------------------
# OAuth schemas
# ---------------------------------------------------------------------------


class OAuthAuthUrlOut(Schema):
    """Response for OAuth authorization URL generation."""

    auth_url: str
    state: str


class OAuthCallbackIn(Schema):
    """Request body for OAuth callback."""

    code: str
    state: str


class OAuthCallbackOut(Schema):
    """Response for OAuth callback processing."""

    success: bool
    connection_id: str
    test_result: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Webhook schemas
# ---------------------------------------------------------------------------


class WebhookEndpointCreateIn(Schema):
    """Request body for creating a webhook endpoint."""

    name: str
    event_type: str
    endpoint_url: str
    secret: str = ""
    headers_json: dict[str, str] = {}
    retry_policy_json: dict[str, Any] = {}
    filter_json: dict[str, Any] = {}


class WebhookEndpointOut(Schema):
    """Response model for a webhook endpoint."""

    id: str
    connection_id: str
    name: str
    event_type: str
    endpoint_url: str
    is_active: bool
    status: str
    last_triggered_at: datetime | None
    created_at: datetime


class WebhookEndpointListOut(Schema):
    """Paginated list of webhook endpoints."""

    items: list[WebhookEndpointOut]
    total: int


class WebhookReceiveOut(Schema):
    """Response for receiving a webhook."""

    success: bool
    event_type: str
    delivery_ids: list[str]
    matched_endpoints: int


class WebhookDeliveryOut(Schema):
    """Response model for a webhook delivery."""

    id: str
    webhook_id: str
    event_type: str
    status: str
    response_status: int | None
    attempt_count: int
    delivered_at: datetime | None
    created_at: datetime


class WebhookDeliveryListOut(Schema):
    """Paginated list of webhook deliveries."""

    items: list[WebhookDeliveryOut]
    total: int


# ---------------------------------------------------------------------------
# Sync schemas
# ---------------------------------------------------------------------------


class SyncTriggerIn(Schema):
    """Request body for triggering a sync."""

    sync_type: str
    direction: str = "inbound"
    conflict_resolution: str = "source_wins"
    field_mappings_json: list[dict[str, Any]] = []
    source_data: list[dict[str, Any]] = []
    target_data: list[dict[str, Any]] = []


class SyncResultOut(Schema):
    """Response for a sync operation."""

    success: bool
    sync_log_id: str
    created: int
    updated: int
    deleted: int
    conflicts: int
    unchanged: int
    total_changes: int
    error: str | None = None


class SyncLogOut(Schema):
    """Response model for a sync log entry."""

    id: str
    connection_id: str
    sync_type: str
    direction: str
    status: str
    records_count: int
    created_count: int
    updated_count: int
    deleted_count: int
    conflict_count: int
    errors_json: list[dict[str, Any]]
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None = None
    created_at: datetime


class SyncLogListOut(Schema):
    """Paginated list of sync logs."""

    items: list[SyncLogOut]
    total: int


# ---------------------------------------------------------------------------
# Health schemas
# ---------------------------------------------------------------------------


class HealthCheckOut(Schema):
    """Response model for a health check."""

    id: str
    connection_id: str
    platform: str
    status: str
    latency_ms: int | None
    error_message: str
    details_json: dict[str, Any]
    last_check_at: datetime | None


class HealthSummaryOut(Schema):
    """Response for connection health summary."""

    latest: dict[str, Any] | None
    history: list[dict[str, Any]]


class HealthBulkOut(Schema):
    """Response for bulk health check."""

    total: int
    healthy: int
    degraded: int
    down: int
    checks: list[dict[str, Any]]


class RateLimitOut(Schema):
    """Response for rate-limit status."""

    allowed: bool
    remaining: int
    limit: int
    retry_after: int = 0


class CircuitBreakerOut(Schema):
    """Response for circuit breaker status."""

    service_id: str
    state: str
    consecutive_failures: int
    half_open_successes: int
    retry_after: int


class CircuitBreakerResetIn(Schema):
    """Request body for resetting a circuit breaker."""

    service_id: str
