"""Manual audit logging and action/resource extraction."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from apps.rbac.auth import VoyagerUser

from .redaction import _redact_sensitive
from .storage import _append_audit_entry

logger = logging.getLogger(__name__)


def _extract_action(request: Any) -> str:
    """Extract the action string from the request.

    Format: ``<resource>.<verb>`` where verb is derived from HTTP method.

    Args:
        request: Django HTTP request object.

    Returns:
        Action string like ``"campaign.created"`` or ``"content.updated"``.
    """
    path = request.path.strip("/")
    parts = path.split("/")

    # Try to find the resource name from the URL path
    # Expected: /api/v1/<resource>/...
    resource = "unknown"
    if len(parts) >= 3:
        resource = parts[2] if parts[0] == "api" else parts[-1]

    method_to_verb = {
        "POST": "created",
        "PUT": "updated",
        "PATCH": "patched",
        "DELETE": "deleted",
    }
    verb = method_to_verb.get(request.method, request.method.lower())

    return f"{resource}.{verb}"


def _extract_resource(request: Any) -> tuple[str, str]:
    """Extract resource type and ID from the request path.

    Args:
        request: Django HTTP request object.

    Returns:
        Tuple of (resource_type, resource_id). resource_id may be empty.
    """
    path = request.path.strip("/")
    parts = path.split("/")

    resource_type = "unknown"
    resource_id = ""

    if len(parts) >= 3 and parts[0] == "api":
        resource_type = parts[2]
        if len(parts) >= 4:
            resource_id = parts[3]

    return resource_type, resource_id


def log_event(
    tenant_id: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    outcome: str = "success",
    details: dict[str, Any] | None = None,
    actor_type: str = "service",
    ip_address: str | None = None,
    user_agent: str = "",
    request_id: str = "",
) -> str | None:
    """Manually log an event from outside HTTP request processing.

    Used by Celery tasks, scheduled jobs, agents, and other non-HTTP
    components to write to the same immutable audit log.

    Args:
        tenant_id: Tenant scope.
        actor_id: ID of the actor (service account, agent ID, etc.).
        action: Action string (e.g. ``"campaign.executed"``).
        resource_type: Type of resource affected.
        resource_id: Resource identifier.
        outcome: ``"success"``, ``"failure"``, or ``"denied"``.
        details: Additional structured data.
        actor_type: ``"user"``, ``"service"``, or ``"agent"``.
        ip_address: Optional IP address.
        user_agent: Optional user agent.
        request_id: Optional correlation ID.

    Returns:
        The hash of the created entry, or ``None`` if logging failed.
    """
    try:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC),
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "outcome": outcome,
            "details": _redact_sensitive(details or {}),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
        }

        entry_hash = _append_audit_entry(entry)

        logger.debug(
            "Manual audit logged: %s (%s) hash=%s",
            action,
            outcome,
            entry_hash[:16],
        )

        return entry_hash

    except Exception as exc:
        logger.error("Failed to create manual audit log entry: %s", exc)
        return None


def _log_entry(
    tenant_id: str,
    user: VoyagerUser | None,
    actor_type: str,
    action: str,
    resource_type: str,
    resource_id: str,
    outcome: str,
    request: Any,
    response: Any | None,
    ip_address: str | None,
    user_agent: str,
    request_id: str,
    duration_ms: float,
    error: str | None = None,
) -> None:
    """Create and append an audit log entry.

    Args:
        tenant_id: Tenant scope.
        user: Authenticated user (may be None).
        actor_type: ``"user"``, ``"service"``, or ``"agent"``.
        action: Classified action string.
        resource_type: Type of resource.
        resource_id: Resource identifier.
        outcome: ``"success"``, ``"failure"``, or ``"denied"``.
        request: Django HTTP request.
        response: Django HTTP response (None on exception).
        ip_address: Client IP.
        user_agent: Client user agent.
        request_id: Correlation ID.
        duration_ms: Request duration in milliseconds.
        error: Optional error message.
    """
    try:
        actor_id = user.user_id if user else "anonymous"

        # Build details dict with redaction
        details: dict[str, Any] = {
            "path": request.path,
            "method": request.method,
            "duration_ms": round(duration_ms, 3),
        }

        # Capture query params (safe ones only)
        query_params = dict(request.GET)
        if query_params:
            details["query_params"] = _redact_sensitive(query_params)

        # Capture request body summary (redacted)
        if hasattr(request, "body") and request.body:
            try:
                import json

                body = json.loads(request.body)
                details["body_keys"] = list(_redact_sensitive(body).keys())
            except (json.JSONDecodeError, TypeError):
                details["body_size"] = len(request.body)

        # Add response status
        if response is not None:
            details["status_code"] = response.status_code

        # Add error if present
        if error:
            details["error"] = error

        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC),
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id or "",
            "outcome": outcome,
            "details": details,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
        }

        entry_hash = _append_audit_entry(entry)

        logger.debug(
            "Audit logged: %s %s (%s) hash=%s",
            action,
            request.path,
            outcome,
            entry_hash[:16],
        )

    except Exception as exc:
        # Audit logging must never break the request
        logger.error("Failed to create audit log entry: %s", exc)
