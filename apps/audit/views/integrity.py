"""Hash chain verification and statistics endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from apps.audit.middleware import _audit_log_store, verify_hash_chain
from apps.audit.serializers import (
    AuditLogStatsSchema,
    HashChainStatusSchema,
)

from .helpers import get_user


def get_audit_stats(
    request: HttpRequest,
    tenant_id: str | None = Query(None, description="Tenant to get stats for"),
    date_from: datetime | None = Query(None, description="Start date (UTC)"),
    date_to: datetime | None = Query(None, description="End date (UTC)"),
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
    user = get_user(request)
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
    events_by_action: dict[str, int] = {}
    events_by_outcome: dict[str, int] = {}
    events_by_resource_type: dict[str, int] = {}
    events_by_day: dict[str, int] = {}
    unique_actors: set[str] = set()

    for entry in entries:
        action = entry["action"]
        events_by_action[action] = events_by_action.get(action, 0) + 1

        outcome = entry["outcome"]
        events_by_outcome[outcome] = events_by_outcome.get(outcome, 0) + 1

        resource_type = entry["resource_type"]
        events_by_resource_type[resource_type] = events_by_resource_type.get(resource_type, 0) + 1

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


def verify_chain(
    request: HttpRequest,
    payload: Any | None = None,
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
    user = get_user(request)
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
