"""Sensitive data redaction for audit logging."""

from __future__ import annotations

from typing import Any

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


def _redact_sensitive(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive fields from request/response data for safe logging.

    Replaces values of known sensitive keys with ``"[REDACTED]"``.

    Args:
        data: Dictionary potentially containing sensitive data.

    Returns:
        Copy of the dictionary with sensitive fields redacted.
    """
    if not isinstance(data, dict):
        return data

    result: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in SENSITIVE_KEYS):
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = _redact_sensitive(value)
        elif isinstance(value, list):
            result[key] = [
                _redact_sensitive(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            result[key] = value
    return result
