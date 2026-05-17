"""Shared helpers for audit views."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from ninja.errors import HttpError

from apps.audit.serializers import AuditLogSchema
from apps.rbac.auth import VoyagerUser


def get_user(request: HttpRequest) -> VoyagerUser:
    """Safely extract VoyagerUser from request."""
    user = getattr(request, "auth", None)
    if user is None or isinstance(user, type(None)):
        raise HttpError(401, "Authentication required")
    return user


def serialize_entry(entry: dict[str, Any]) -> AuditLogSchema:
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
