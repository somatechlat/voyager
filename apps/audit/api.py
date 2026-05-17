"""
Audit Log API endpoints for Voyager.

Provides query, export, and integrity verification endpoints for the
immutable audit log. All entries are read-only after creation.

Endpoint Summary:
- ``GET /api/v1/audit-logs`` — Query audit logs (paginated, filterable)
- ``GET /api/v1/audit-logs/{id}`` — Single entry
- ``GET /api/v1/audit-logs/export`` — Export (CSV/JSON)
- ``GET /api/v1/audit-logs/stats`` — Statistics for tenant
- ``POST /api/v1/audit-logs/verify`` — Verify hash chain integrity
- ``POST /api/v1/audit-logs`` — Manual entry creation (for services)
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from ninja import Router, Query
from ninja.errors import HttpError

from apps.rbac.auth import (
    VoyagerKeycloakBearer,
    VoyagerUser,
    get_current_user,
)
from apps.audit.middleware import (
    _audit_log_store,
    get_last_hash,
    log_event,
    verify_hash_chain,
    _redact_sensitive,
)
from apps.audit.serializers import (
    AuditLogSchema,
    AuditLogListResponse,
    AuditLogCreateSchema,
    AuditLogFilterSchema,
    AuditLogStatsSchema,
    AuditLogExportRequestSchema,
    AuditLogExportResponse,
    HashChainStatusSchema,
    HashChainVerifyRequestSchema,
    BulkAuditLogCreateSchema,
    BulkAuditLogResponse,
)

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user(request: HttpRequest) -> VoyagerUser:
    """Safely extract VoyagerUser from request."""
    user = getattr(request, "auth", None)
    if user is None or isinstance(user, type(None)):
        raise HttpError(401, "Authentication required")
    return user


def _serialize_entry(entry: Dict[str, Any]) -> AuditLogSchema:
    """Convert raw audit log entry dict to schema."""
    return AuditLogSchema(
        id=entry["id"],
        timestamp=entry["timestamp"],
        tenant_id=entry["tenant_id"],
        actor_id=entry["actor_id"],
        actor_type=entry["actor_type"],
        action=entry["action"],
        resource_type=entry["resource_type"],
        resource_id=entry["resource_id"],
        outcome=entry["outcome"],
        details=entry.get("details", {}),
        ip_address=entry.get("ip_address"),
        user_agent=entry.get("user_agent", ""),
        request_id=entry.get("request_id", ""),
        previous_hash=entry.get("previous_hash", ""),
        hash=entry["hash"],
    )


# ---------------------------------------------------------------------------
# Query endpoints
# ---------------------------------------------------------------------------


@router.get("/audit-logs", response=AuditLogListResponse)
def query_audit_logs(
    request: HttpRequest,
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    actor_id: Optional[str] = Query(None, description="Filter by actor"),
    actor_type: Optional[str] = Query(None, description="Filter by actor type"),
    action: Optional[str] = Query(None, description="Filter by action"),
    action_prefix: Optional[str] = Query(None, description="Filter by action prefix"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    outcome: Optional[str] = Query(None, description="Filter by outcome"),
    date_from: Optional[datetime] = Query(None, description="Start date (UTC)"),
    date_to: Optional[datetime] = Query(None, description="End date (UTC)"),
    request_id: Optional[str] = Query(None, description="Filter by request ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
) -> AuditLogListResponse:
    """Query audit logs with filtering and pagination.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        actor_id: Filter by actor user/service ID.
        actor_type: Filter by ``"user"``, ``"service"``, or ``"agent"``.
        action: Exact action match.
        action_prefix: Prefix match for actions (e.g. ``"campaign."``).
        resource_type: Filter by resource type.
        resource_id: Filter by resource ID.
        outcome: Filter by ``"success"``, ``"failure"``, or ``"denied"``.
        date_from: Inclusive start date.
        date_to: Inclusive end date.
        request_id: Filter by correlation ID.
        page: Page number (1-indexed).
        page_size: Entries per page.

    Returns:
        Paginated audit log list.

    Raises:
        HttpError: 403 if user lacks audit read permission.
    """
    user = _get_user(request)
    if not (
        user.has_permission("voyager:audit:*")
        or user.has_permission("voyager:read:*")
        or user.is_tenant_admin()
    ):
        raise HttpError(403, "Permission denied: audit read access required")

    entries = list(_audit_log_store)

    # Apply tenant filter (non-superadmins can only see their tenant)
    if not user.is_superadmin():
        entries = [e for e in entries if e["tenant_id"] == user.tenant_id]
    elif tenant_id:
        entries = [e for e in entries if e["tenant_id"] == tenant_id]

    # Apply remaining filters
    if actor_id:
        entries = [e for e in entries if e["actor_id"] == actor_id]
    if actor_type:
        entries = [e for e in entries if e["actor_type"] == actor_type]
    if action:
        entries = [e for e in entries if e["action"] == action]
    if action_prefix:
        entries = [e for e in entries if e["action"].startswith(action_prefix)]
    if resource_type:
        entries = [e for e in entries if e["resource_type"] == resource_type]
    if resource_id:
        entries = [e for e in entries if e["resource_id"] == resource_id]
    if outcome:
        entries = [e for e in entries if e["outcome"] == outcome]
    if date_from:
        entries = [e for e in entries if e["timestamp"] >= date_from]
    if date_to:
        entries = [e for e in entries if e["timestamp"] <= date_to]
    if request_id:
        entries = [e for e in entries if e.get("request_id") == request_id]

    # Sort by timestamp descending (newest first)
    entries.sort(key=lambda e: e["timestamp"], reverse=True)

    total = len(entries)
    start = (page - 1) * page_size
    end = start + page_size
    page_entries = entries[start:end]

    items = [_serialize_entry(e) for e in page_entries]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/audit-logs/{entry_id}", response=AuditLogSchema)
def get_audit_log_entry(
    request: HttpRequest,
    entry_id: UUID,
) -> AuditLogSchema:
    """Get a single audit log entry by ID.

    Args:
        request: HTTP request.
        entry_id: UUID of the entry.

    Returns:
        The audit log entry.

    Raises:
        HttpError: 404 if entry not found.
        HttpError: 403 if user lacks permission.
    """
    user = _get_user(request)
    if not (
        user.has_permission("voyager:audit:*")
        or user.has_permission("voyager:read:*")
        or user.is_tenant_admin()
    ):
        raise HttpError(403, "Permission denied")

    for entry in _audit_log_store:
        if str(entry["id"]) == str(entry_id):
            # Tenant isolation check
            if not user.is_superadmin() and entry["tenant_id"] != user.tenant_id:
                raise HttpError(403, "Access denied: cross-tenant audit access")
            return _serialize_entry(entry)

    raise HttpError(404, f"Audit log entry {entry_id} not found")


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------


@router.get("/audit-logs/export")
def export_audit_logs(
    request: HttpRequest,
    format: str = Query("json", description="Export format: json or csv"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    date_from: Optional[datetime] = Query(None, description="Start date (UTC)"),
    date_to: Optional[datetime] = Query(None, description="End date (UTC)"),
    action_prefix: Optional[str] = Query(None, description="Filter by action prefix"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
) -> HttpResponse:
    """Export audit logs as CSV or JSON.

    Args:
        request: HTTP request.
        format: ``"json"`` or ``"csv"``.
        tenant_id: Filter by tenant.
        date_from: Inclusive start date.
        date_to: Inclusive end date.
        action_prefix: Filter by action prefix.
        resource_type: Filter by resource type.

    Returns:
        HTTP response with appropriate Content-Type and attachment disposition.

    Raises:
        HttpError: 400 for invalid format.
        HttpError: 403 for insufficient permissions.
    """
    user = _get_user(request)
    if not (
        user.has_permission("voyager:audit:*")
        or user.has_permission("voyager:export:data")
        or user.is_tenant_admin()
    ):
        raise HttpError(403, "Permission denied: export access required")

    # Collect matching entries
    entries = list(_audit_log_store)

    if not user.is_superadmin():
        entries = [e for e in entries if e["tenant_id"] == user.tenant_id]
    elif tenant_id:
        entries = [e for e in entries if e["tenant_id"] == tenant_id]

    if date_from:
        entries = [e for e in entries if e["timestamp"] >= date_from]
    if date_to:
        entries = [e for e in entries if e["timestamp"] <= date_to]
    if action_prefix:
        entries = [e for e in entries if e["action"].startswith(action_prefix)]
    if resource_type:
        entries = [e for e in entries if e["resource_type"] == resource_type]

    # Sort by timestamp
    entries.sort(key=lambda e: e["timestamp"])

    if format.lower() == "json":
        return _export_json(entries)
    elif format.lower() == "csv":
        return _export_csv(entries)
    else:
        raise HttpError(400, f"Unsupported export format: {format}")


def _export_json(entries: List[Dict[str, Any]]) -> HttpResponse:
    """Export entries as JSON.

    Args:
        entries: List of audit log entry dictionaries.

    Returns:
        JSON HTTP response with attachment header.
    """
    data = []
    for entry in entries:
        data.append({
            "id": str(entry["id"]),
            "timestamp": entry["timestamp"].isoformat(),
            "tenant_id": entry["tenant_id"],
            "actor_id": entry["actor_id"],
            "actor_type": entry["actor_type"],
            "action": entry["action"],
            "resource_type": entry["resource_type"],
            "resource_id": entry["resource_id"],
            "outcome": entry["outcome"],
            "details": _redact_sensitive(entry.get("details", {})),
            "ip_address": entry.get("ip_address"),
            "user_agent": entry.get("user_agent", ""),
            "request_id": entry.get("request_id", ""),
            "previous_hash": entry.get("previous_hash", ""),
            "hash": entry["hash"],
        })

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    response = HttpResponse(
        json.dumps(data, indent=2, default=str),
        content_type="application/json",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="audit_log_{timestamp}.json"'
    )
    return response


def _export_csv(entries: List[Dict[str, Any]]) -> HttpResponse:
    """Export entries as CSV.

    Args:
        entries: List of audit log entry dictionaries.

    Returns:
        CSV HTTP response with attachment header.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "id",
        "timestamp",
        "tenant_id",
        "actor_id",
        "actor_type",
        "action",
        "resource_type",
        "resource_id",
        "outcome",
        "ip_address",
        "request_id",
        "hash",
    ])

    for entry in entries:
        writer.writerow([
            str(entry["id"]),
            entry["timestamp"].isoformat(),
            entry["tenant_id"],
            entry["actor_id"],
            entry["actor_type"],
            entry["action"],
            entry["resource_type"],
            entry["resource_id"],
            entry["outcome"],
            entry.get("ip_address", ""),
            entry.get("request_id", ""),
            entry["hash"],
        ])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    response = HttpResponse(
        output.getvalue(),
        content_type="text/csv",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="audit_log_{timestamp}.csv"'
    )
    return response


# ---------------------------------------------------------------------------
# Statistics endpoint
# ---------------------------------------------------------------------------


@router.get("/audit-logs/stats", response=AuditLogStatsSchema)
def get_audit_stats(
    request: HttpRequest,
    tenant_id: Optional[str] = Query(None, description="Tenant to get stats for"),
    date_from: Optional[datetime] = Query(None, description="Start date (UTC)"),
    date_to: Optional[datetime] = Query(None, description="End date (UTC)"),
) -> AuditLogStatsSchema:
    """Get aggregated statistics for audit log entries.

    Args:
        request: HTTP request.
        tenant_id: Tenant scope (defaults to current user's tenant).
        date_from: Start of date range.
        date_to: End of date range.

    Returns:
        Aggregated statistics including event counts by action, outcome,
        resource type, and day.
    """
    user = _get_user(request)
    if not (
        user.has_permission("voyager:audit:*")
        or user.has_permission("voyager:read:analytics")
        or user.is_tenant_admin()
    ):
        raise HttpError(403, "Permission denied")

    target_tenant = tenant_id or user.tenant_id

    # Filter entries
    entries = [e for e in _audit_log_store if e["tenant_id"] == target_tenant]

    if date_from:
        entries = [e for e in entries if e["timestamp"] >= date_from]
    if date_to:
        entries = [e for e in entries if e["timestamp"] <= date_to]

    # Compute aggregates
    events_by_action: Dict[str, int] = {}
    events_by_outcome: Dict[str, int] = {}
    events_by_resource_type: Dict[str, int] = {}
    events_by_day: Dict[str, int] = {}
    unique_actors: set[str] = set()

    for entry in entries:
        action = entry["action"]
        events_by_action[action] = events_by_action.get(action, 0) + 1

        outcome = entry["outcome"]
        events_by_outcome[outcome] = events_by_outcome.get(outcome, 0) + 1

        resource_type = entry["resource_type"]
        events_by_resource_type[resource_type] = (
            events_by_resource_type.get(resource_type, 0) + 1
        )

        day = entry["timestamp"].strftime("%Y-%m-%d")
        events_by_day[day] = events_by_day.get(day, 0) + 1

        unique_actors.add(entry["actor_id"])

    return AuditLogStatsSchema(
        tenant_id=target_tenant,
        total_events=len(entries),
        events_by_action=events_by_action,
        events_by_outcome=events_by_outcome,
        events_by_resource_type=events_by_resource_type,
        events_by_day=events_by_day,
        unique_actors=len(unique_actors),
        date_from=date_from,
        date_to=date_to,
    )


# ---------------------------------------------------------------------------
# Hash chain verification
# ---------------------------------------------------------------------------


@router.post("/audit-logs/verify", response=HashChainStatusSchema)
def verify_chain(
    request: HttpRequest,
    payload: Optional[Any] = None,
) -> HashChainStatusSchema:
    """Verify the integrity of the audit log hash chain.

    Re-computes all hashes and checks chain linkage. Returns detailed
    information about any break in the chain.

    Args:
        request: HTTP request.
        payload: Optional filter (tenant_id, date range).

    Returns:
        Hash chain verification status.
    """
    user = _get_user(request)
    if not (
        user.has_permission("voyager:audit:*")
        or user.is_tenant_admin()
        or user.has_role("voyager-compliance-officer")
    ):
        raise HttpError(403, "Permission denied: audit verification access required")

    tenant_id = None
    if payload and hasattr(payload, "tenant_id"):
        tenant_id = payload.tenant_id
    if not tenant_id:
        tenant_id = user.tenant_id

    result = verify_hash_chain(tenant_id=tenant_id)

    return HashChainStatusSchema(
        is_valid=result["is_valid"],
        total_entries=result["total_entries"],
        first_entry_id=result["first_entry_id"],
        last_entry_id=result["last_entry_id"],
        last_hash=result["last_hash"],
        broken_at_index=result["broken_at_index"],
        broken_entry_id=result["broken_entry_id"],
        checked_at=result["checked_at"],
    )


# ---------------------------------------------------------------------------
# Manual entry creation
# ---------------------------------------------------------------------------


@router.post("/audit-logs")
def create_audit_entry(
    request: HttpRequest,
    payload: AuditLogCreateSchema,
) -> Dict[str, str]:
    """Manually create an audit log entry.

    Used by services, agents, and Celery tasks to log non-HTTP events.

    Args:
        request: HTTP request.
        payload: Audit entry data.

    Returns:
        Dictionary with ``status`` and ``hash`` of the created entry.

    Raises:
        HttpError: 403 if user lacks audit write permission.
    """
    user = _get_user(request)
    if not (
        user.has_permission("voyager:audit:*")
        or user.has_permission("voyager:write:*")
        or user.is_tenant_admin()
    ):
        raise HttpError(403, "Permission denied: audit write access required")

    entry_hash = log_event(
        tenant_id=payload.tenant_id,
        actor_id=payload.actor_id,
        action=payload.action,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        outcome=payload.outcome,
        details=payload.details,
        actor_type=payload.actor_type,
        ip_address=payload.ip_address,
        user_agent=request.headers.get("User-Agent", ""),
        request_id=request.headers.get("X-Request-ID", ""),
    )

    if entry_hash:
        return {"status": "created", "hash": entry_hash}
    raise HttpError(500, "Failed to create audit log entry")


# ---------------------------------------------------------------------------
# Bulk entry creation
# ---------------------------------------------------------------------------


@router.post("/audit-logs/bulk")
def create_bulk_audit_entries(
    request: HttpRequest,
    payload: BulkAuditLogCreateSchema,
) -> BulkAuditLogResponse:
    """Create multiple audit log entries in a single request.

    Args:
        request: HTTP request.
        payload: List of audit entries to create.

    Returns:
        Summary of created and failed entries.

    Raises:
        HttpError: 403 for insufficient permissions.
        HttpError: 400 if payload exceeds maximum batch size.
    """
    user = _get_user(request)
    if not (
        user.has_permission("voyager:audit:*")
        or user.is_tenant_admin()
    ):
        raise HttpError(403, "Permission denied")

    MAX_BATCH_SIZE = 100
    if len(payload.entries) > MAX_BATCH_SIZE:
        raise HttpError(400, f"Batch size exceeds maximum of {MAX_BATCH_SIZE}")

    created_count = 0
    failed_count = 0
    errors: List[str] = []

    for i, entry_payload in enumerate(payload.entries):
        try:
            entry_hash = log_event(
                tenant_id=entry_payload.tenant_id,
                actor_id=entry_payload.actor_id,
                action=entry_payload.action,
                resource_type=entry_payload.resource_type,
                resource_id=entry_payload.resource_id,
                outcome=entry_payload.outcome,
                details=entry_payload.details,
                actor_type=entry_payload.actor_type,
                ip_address=entry_payload.ip_address,
                request_id=request.headers.get("X-Request-ID", ""),
            )
            if entry_hash:
                created_count += 1
            else:
                failed_count += 1
                errors.append(f"Entry {i}: returned None")
        except Exception as exc:
            failed_count += 1
            errors.append(f"Entry {i}: {exc}")

    return BulkAuditLogResponse(
        created_count=created_count,
        failed_count=failed_count,
        errors=errors,
    )
