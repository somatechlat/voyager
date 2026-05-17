"""Audit log export endpoints (CSV/JSON)."""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import UTC, datetime
from typing import Any

from django.http import HttpRequest, HttpResponse
from ninja import Query
from ninja.errors import HttpError

from apps.audit.middleware import _audit_log_store, _redact_sensitive

from .helpers import get_user

logger = logging.getLogger(__name__)


def export_audit_logs(
    request: HttpRequest,
    format: str = Query("json", description="Export format: json or csv"),
    tenant_id: str | None = Query(None, description="Filter by tenant"),
    date_from: datetime | None = Query(None, description="Start date (UTC)"),
    date_to: datetime | None = Query(None, description="End date (UTC)"),
    action_prefix: str | None = Query(None, description="Filter by action prefix"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
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
    user = get_user(request)
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


def _export_json(entries: list[dict[str, Any]]) -> HttpResponse:
    """Export entries as JSON.

    Args:
        entries: List of audit log entry dictionaries.

    Returns:
        JSON HTTP response with attachment header.
    """
    data = []
    for entry in entries:
        data.append(
            {
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
            }
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    response = HttpResponse(
        json.dumps(data, indent=2, default=str),
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="audit_log_{timestamp}.json"'
    return response


def _export_csv(entries: list[dict[str, Any]]) -> HttpResponse:
    """Export entries as CSV.

    Args:
        entries: List of audit log entry dictionaries.

    Returns:
        CSV HTTP response with attachment header.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(
        [
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
        ]
    )

    for entry in entries:
        writer.writerow(
            [
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
            ]
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    response = HttpResponse(
        output.getvalue(),
        content_type="text/csv",
    )
    response["Content-Disposition"] = f'attachment; filename="audit_log_{timestamp}.csv"'
    return response
