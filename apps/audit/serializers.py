"""
Pydantic schemas (Django Ninja Serializers) for Voyager Audit Logging.

Defines request/response models for audit log entries, including hash-chain
integrity, filtering, and export support. All timestamps are UTC.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ninja import Schema


# ---------------------------------------------------------------------------
# Core audit schemas
# ---------------------------------------------------------------------------

class AuditLogSchema(Schema):
    """Represents a single immutable audit log entry.

    Attributes:
        id: Unique UUID for the log entry.
        timestamp: When the event occurred (UTC).
        tenant_id: Tenant scope for the event.
        actor_id: Keycloak ``sub`` of the user who triggered the event.
        actor_type: Type of actor — ``"user"``, ``"service"``, or ``"agent"``.
        action: Action string (e.g. ``"content.created"``, ``"campaign.updated"``).
        resource_type: Type of resource affected (e.g. ``"campaign"``, ``"content"``).
        resource_id: Identifier of the affected resource.
        outcome: Result — ``"success"``, ``"failure"``, or ``"denied"``.
        details: Arbitrary JSON with additional event context.
        ip_address: Client IP address.
        user_agent: Client user agent string.
        request_id: Correlation ID from ``X-Request-ID`` header.
        previous_hash: SHA-256 hash of the previous log entry (hash chain).
        hash: SHA-256 hash of this entry's canonical representation.
    """

    id: UUID
    timestamp: datetime
    tenant_id: str
    actor_id: str
    actor_type: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: str = ""
    request_id: str = ""
    previous_hash: str = ""
    hash: str


class AuditLogListResponse(Schema):
    """Paginated response for audit log queries."""

    items: List[AuditLogSchema]
    total: int
    page: int
    page_size: int


class AuditLogCreateSchema(Schema):
    """Request body for manually creating an audit log entry.

    Used by internal services that need to log events outside of HTTP
    request processing (e.g. Celery tasks, scheduled jobs).
    """

    tenant_id: str
    actor_id: str
    actor_type: str = "service"
    action: str
    resource_type: str
    resource_id: str
    outcome: str = "success"
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None


class AuditLogFilterSchema(Schema):
    """Query parameters for filtering audit logs.

    All filters are AND-combined. Date range uses inclusive boundaries.
    """

    tenant_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    action: Optional[str] = None
    action_prefix: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    outcome: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    request_id: Optional[str] = None
    page: int = 1
    page_size: int = 20


class AuditLogStatsSchema(Schema):
    """Aggregated statistics for audit log queries."""

    tenant_id: str
    total_events: int
    events_by_action: Dict[str, int]
    events_by_outcome: Dict[str, int]
    events_by_resource_type: Dict[str, int]
    events_by_day: Dict[str, int]
    unique_actors: int
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Export schemas
# ---------------------------------------------------------------------------

class AuditLogExportRequestSchema(Schema):
    """Request body for exporting audit logs.

    Supports CSV and JSON output formats with optional filtering.
    """

    format: str = "json"  # "csv" or "json"
    tenant_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    action_prefix: Optional[str] = None
    resource_type: Optional[str] = None


class AuditLogExportResponse(Schema):
    """Response for audit log export."""

    format: str
    record_count: int
    download_url: Optional[str] = None
    data: Optional[List[AuditLogSchema]] = None


# ---------------------------------------------------------------------------
# Hash chain verification schemas
# ---------------------------------------------------------------------------

class HashChainStatusSchema(Schema):
    """Status of the hash chain integrity check."""

    is_valid: bool
    total_entries: int
    first_entry_id: Optional[str] = None
    last_entry_id: Optional[str] = None
    last_hash: str = ""
    broken_at_index: Optional[int] = None
    broken_entry_id: Optional[str] = None
    checked_at: datetime


class HashChainVerifyRequestSchema(Schema):
    """Request to verify hash chain integrity for a tenant's audit log."""

    tenant_id: str
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Bulk operation schemas
# ---------------------------------------------------------------------------

class BulkAuditLogCreateSchema(Schema):
    """Request body for creating multiple audit log entries at once.

    Used for batch-logging from background tasks or bulk imports.
    """

    entries: List[AuditLogCreateSchema]


class BulkAuditLogResponse(Schema):
    """Response for bulk audit log creation."""

    created_count: int
    failed_count: int
    errors: List[str]
