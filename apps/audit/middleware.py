"""
Audit middleware for Voyager.

Automatically logs all mutating HTTP requests (POST, PUT, PATCH, DELETE) to
the audit log with hash-chain integrity. Immutable by design — entries are
never updated or deleted after creation.

The hash chain links each entry to the previous one via SHA-256:
    hash[n] = SHA-256(hash[n-1] + canonical(entry[n]))

This ensures tamper-evidence: modifying any entry breaks the chain.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from ninja.errors import HttpError

from apps.rbac.auth import VoyagerUser, get_optional_user

logger = logging.getLogger(__name__)

# In-memory audit log storage — replaced by database-backed model in production.
# Protected by module-level access only; no external modification allowed.
_audit_log_store: List[Dict[str, Any]] = []
_last_hash: str = "0" * 64  # Genesis hash

# Actions to exclude from automatic audit logging
SKIP_PATHS = {
    "/health",
    "/ready",
    "/healthz",
    "/readyz",
    "/api/v1/audit-logs",  # Don't audit the audit endpoint itself
}

# Content types that may contain sensitive data to be redacted
SENSITIVE_KEYS = {
    "password",
    "token",
    "secret",
    "api_key",
    "client_secret",
    "credit_card",
    "ssn",
    "authorization",
    "cookie",
}


def _canonical_json(data: Dict[str, Any]) -> str:
    """Create a deterministic JSON representation for hashing.

    Sorts keys recursively to ensure the same data always produces the
    same canonical string regardless of insertion order.

    Args:
        data: Dictionary to serialise.

    Returns:
        Deterministic JSON string with sorted keys.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _redact_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields from request/response data for safe logging.

    Replaces values of known sensitive keys with ``"[REDACTED]"``.

    Args:
        data: Dictionary potentially containing sensitive data.

    Returns:
        Copy of the dictionary with sensitive fields redacted.
    """
    if not isinstance(data, dict):
        return data

    result: Dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in SENSITIVE_KEYS):
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = _redact_sensitive(value)
        elif isinstance(value, list):
            result[key] = [
                _redact_sensitive(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def _compute_hash(previous_hash: str, entry_data: Dict[str, Any]) -> str:
    """Compute the SHA-256 hash for an audit log entry.

    The hash covers the previous entry's hash (chaining) and the canonical
    representation of the current entry.

    Args:
        previous_hash: SHA-256 hex string of the previous entry.
        entry_data: Dictionary of the current entry's fields.

    Returns:
        SHA-256 hex string for this entry.
    """
    canonical = _canonical_json(entry_data)
    combined = f"{previous_hash}:{canonical}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _append_audit_entry(entry: Dict[str, Any]) -> str:
    """Append an entry to the audit log with hash-chain integrity.

    This is the ONLY function that writes to ``_audit_log_store``.

    Args:
        entry: Audit entry dictionary (without hash field).

    Returns:
        The computed hash for the entry.
    """
    global _last_hash

    # Compute hash covering previous hash + entry content
    entry_hash = _compute_hash(_last_hash, entry)

    entry["previous_hash"] = _last_hash
    entry["hash"] = entry_hash
    entry["id"] = str(entry.get("id", _generate_entry_id()))

    _audit_log_store.append(entry)
    _last_hash = entry_hash

    return entry_hash


def _generate_entry_id() -> str:
    """Generate a unique entry identifier.

    Returns:
        UUID4 string.
    """
    import uuid

    return str(uuid.uuid4())


def get_audit_log_store() -> List[Dict[str, Any]]:
    """Get a read-only copy of the audit log store.

    Returns:
        Shallow copy of the audit log entries list.
    """
    return list(_audit_log_store)


def get_last_hash() -> str:
    """Get the last hash in the chain for external verification.

    Returns:
        SHA-256 hex string of the most recent entry.
    """
    return _last_hash


class AuditMiddleware:
    """Automatically log all mutating HTTP requests with hash-chain integrity.

    This middleware intercepts POST, PUT, PATCH, and DELETE requests and
creates an immutable audit log entry with:
    - Actor identification (from JWT)
    - Action classification
    - Resource identification
    - Outcome (success/failure/denied)
    - Hash chain linking to previous entries

    Attributes:
        get_response: Django get_response callable.
    """

    # HTTP methods that trigger audit logging
    MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        """Process the request through audit logging.

        Args:
            request: Django HTTP request object.

        Returns:
            HTTP response from downstream handlers.
        """
        # Only audit mutating methods
        if request.method not in self.MUTATING_METHODS:
            return self.get_response(request)

        # Skip health/readiness and audit endpoints
        if any(request.path.startswith(p) for p in SKIP_PATHS):
            return self.get_response(request)

        # Only audit API routes
        if not request.path.startswith("/api/"):
            return self.get_response(request)

        start_time = time.monotonic()

        # Capture pre-request state
        user = get_optional_user(request)
        action = self._extract_action(request)
        resource_type, resource_id = self._extract_resource(request)
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        request_id = request.headers.get("X-Request-ID", "")
        tenant_id = request.headers.get("X-Tenant-ID", user.tenant_id if user else "default")

        try:
            response = self.get_response(request)
            duration_ms = (time.monotonic() - start_time) * 1000

            if self._should_log(request, response):
                outcome = "success" if response.status_code < 400 else "failure"
                self._log_entry(
                    tenant_id=tenant_id,
                    user=user,
                    actor_type="user" if user else "service",
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    outcome=outcome,
                    request=request,
                    response=response,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_id=request_id,
                    duration_ms=duration_ms,
                )

            return response

        except HttpError as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            self._log_entry(
                tenant_id=tenant_id,
                user=user,
                actor_type="user" if user else "service",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                outcome="denied" if exc.status_code == 403 else "failure",
                request=request,
                response=None,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise

        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            self._log_entry(
                tenant_id=tenant_id,
                user=user,
                actor_type="user" if user else "service",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                outcome="failure",
                request=request,
                response=None,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise

    def _should_log(self, request: Any, response: Any) -> bool:
        """Determine if the request/response pair should be logged.

        Args:
            request: Django HTTP request object.
            response: Django HTTP response object.

        Returns:
            ``True`` if the interaction should be audited.
        """
        # Always log mutating operations on API endpoints
        return True

    def _extract_action(self, request: Any) -> str:
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

    def _extract_resource(self, request: Any) -> Tuple[str, str]:
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

    def _get_client_ip(self, request: Any) -> Optional[str]:
        """Extract the client's real IP address, respecting proxies.

        Checks ``X-Forwarded-For`` and ``X-Real-IP`` headers before falling
        back to ``REMOTE_ADDR``.

        Args:
            request: Django HTTP request object.

        Returns:
            IP address string, or ``None`` if unavailable.
        """
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            # Take the first IP in the chain (closest to the client)
            return x_forwarded_for.split(",")[0].strip()

        x_real_ip = request.headers.get("X-Real-IP")
        if x_real_ip:
            return x_real_ip.strip()

        return request.META.get("REMOTE_ADDR")

    def _log_entry(
        self,
        tenant_id: str,
        user: Optional[VoyagerUser],
        actor_type: str,
        action: str,
        resource_type: str,
        resource_id: str,
        outcome: str,
        request: Any,
        response: Optional[Any],
        ip_address: Optional[str],
        user_agent: str,
        request_id: str,
        duration_ms: float,
        error: Optional[str] = None,
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
            details: Dict[str, Any] = {
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

            entry: Dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc),
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


# ---------------------------------------------------------------------------
# Manual audit logging for non-HTTP events
# ---------------------------------------------------------------------------


def log_event(
    tenant_id: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    outcome: str = "success",
    details: Optional[Dict[str, Any]] = None,
    actor_type: str = "service",
    ip_address: Optional[str] = None,
    user_agent: str = "",
    request_id: str = "",
) -> Optional[str]:
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
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc),
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


def verify_hash_chain(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Verify the integrity of the audit log hash chain.

    Re-computes hashes for all entries and checks each link in the chain.

    Args:
        tenant_id: If provided, only verify entries for this tenant.

    Returns:
        Verification result with ``is_valid``, ``total_entries``, and
        if broken, ``broken_at_index`` and ``broken_entry_id``.
    """
    entries = _audit_log_store
    if tenant_id:
        entries = [e for e in entries if e["tenant_id"] == tenant_id]

    if not entries:
        return {
            "is_valid": True,
            "total_entries": 0,
            "first_entry_id": None,
            "last_entry_id": None,
            "last_hash": "",
            "broken_at_index": None,
            "broken_entry_id": None,
            "checked_at": datetime.now(timezone.utc),
        }

    previous_hash = entries[0]["previous_hash"]

    for i, entry in enumerate(entries):
        # Recompute hash
        entry_copy = {k: v for k, v in entry.items() if k not in ("hash", "previous_hash")}
        entry_copy["id"] = str(entry["id"])
        entry_copy["timestamp"] = entry["timestamp"].isoformat()
        computed = _compute_hash(previous_hash, entry_copy)

        if computed != entry["hash"]:
            return {
                "is_valid": False,
                "total_entries": len(entries),
                "first_entry_id": str(entries[0]["id"]),
                "last_entry_id": str(entries[-1]["id"]),
                "last_hash": entries[-1]["hash"],
                "broken_at_index": i,
                "broken_entry_id": str(entry["id"]),
                "checked_at": datetime.now(timezone.utc),
            }

        previous_hash = entry["hash"]

    return {
        "is_valid": True,
        "total_entries": len(entries),
        "first_entry_id": str(entries[0]["id"]),
        "last_entry_id": str(entries[-1]["id"]),
        "last_hash": entries[-1]["hash"],
        "broken_at_index": None,
        "broken_entry_id": None,
        "checked_at": datetime.now(timezone.utc),
    }
