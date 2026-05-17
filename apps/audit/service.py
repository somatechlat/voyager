"""
Audit Service.

Non-blocking audit log writing service.
Used by middleware and views to record audit events.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def log_audit_event(
    tenant_id: str,
    actor_id: str,
    actor_type: str,
    action: str,
    resource_type: str,
    resource_id: str,
    outcome: str,
    details: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: str = "",
    request_id: str = "",
    previous_hash: str = "",
) -> None:
    """
    Write an audit log entry.

    This function is designed to be non-blocking — it logs the event
    and continues. In production, this should write to the database
    or an async task queue.

    Args:
        tenant_id: The tenant scope.
        actor_id: The ID of the actor (user/service/agent).
        actor_type: Type of actor ("user", "service", "agent").
        action: The action performed (e.g., "content.created").
        resource_type: The type of resource affected.
        resource_id: The ID of the resource affected.
        outcome: Result ("success", "failure", "denied").
        details: Additional JSON-serializable details.
        ip_address: Client IP address.
        user_agent: Client user agent string.
        request_id: Request ID for correlation.
        previous_hash: Previous log entry hash for chain integrity.
    """
    try:
        # Compute hash of this record for chain integrity
        record_data = json.dumps({
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "actor_type": actor_type,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "outcome": outcome,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
            "previous_hash": previous_hash,
        }, sort_keys=True)
        record_hash = hashlib.sha256(record_data.encode()).hexdigest()

        # TODO: Write to AuditLogEntry model or send to async task
        logger.info(
            "AUDIT: tenant=%s actor=%s action=%s resource=%s outcome=%s hash=%s",
            tenant_id,
            actor_id,
            action,
            f"{resource_type}:{resource_id}",
            outcome,
            record_hash[:16],
        )
    except Exception as exc:
        # Audit logging must never break the request
        logger.warning("Failed to write audit log: %s", exc)
