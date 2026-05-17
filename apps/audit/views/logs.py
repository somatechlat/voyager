"""Audit log query and creation endpoints."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from apps.audit.middleware import _audit_log_store, log_event
from apps.audit.serializers import (
    AuditLogCreateSchema,
    AuditLogListResponse,
    BulkAuditLogCreateSchema,
    BulkAuditLogResponse,
)

from .helpers import get_user, serialize_entry

logger = logging.getLogger(__name__)


def query_audit_logs(
    request: HttpRequest,
    tenant_id: str | None = Query(None, description="Filter by tenant"),
    actor_id: str | None = Query(None, description="Filter by actor"),
    actor_type: str | None = Query(None, description="Filter by actor type"),
    action: str | None = Query(None, description="Filter by action"),
    action_prefix: str | None = Query(None, description="Filter by action prefix"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    outcome: str | None = Query(None, description="Filter by outcome"),
    date_from: datetime | None = Query(None, description="Start date (UTC)"),
    date_to: datetime | None = Query(None, description="End date (UTC)"),
    request_id: str | None = Query(None, description="Filter by request ID"),
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
    user = get_user(request)
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

    items = [serialize_entry(e) for e in page_entries]

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def get_audit_log_entry(
    request: HttpRequest,
    entry_id: UUID,
) -> Any:
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
    user = get_user(request)
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
            return serialize_entry(entry)

    raise HttpError(404, f"Audit log entry {entry_id} not found")


def create_audit_entry(
    request: HttpRequest,
    payload: AuditLogCreateSchema,
) -> dict[str, str]:
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
    user = get_user(request)
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
    user = get_user(request)
    if not (user.has_permission("voyager:audit:*") or user.is_tenant_admin()):
        raise HttpError(403, "Permission denied")

    max_batch_size = 100
    if len(payload.entries) > max_batch_size:
        raise HttpError(400, f"Batch size exceeds maximum of {max_batch_size}")

    created_count = 0
    failed_count = 0
    errors: list[str] = []

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
