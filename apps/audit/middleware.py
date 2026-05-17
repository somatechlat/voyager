"""Audit middleware for Voyager (backward-compatible re-export).

This module re-exports all symbols from ``apps.audit.middleware`` subpackage
for backward compatibility. Use ``from apps.audit.middleware import X`` as before.
"""

from apps.audit.middleware import (  # noqa: F401
    SENSITIVE_KEYS,
    SKIP_PATHS,
    _audit_log_store,
    _extract_action,
    _extract_resource,
    _last_hash,
    _redact_sensitive,
    get_audit_log_store,
    get_last_hash,
    log_event,
    verify_hash_chain,
)
from apps.audit.middleware.middleware import AuditMiddleware  # noqa: F401

__all__ = [
    "AuditMiddleware",
    "SKIP_PATHS",
    "SENSITIVE_KEYS",
    "_audit_log_store",
    "_extract_action",
    "_extract_resource",
    "_last_hash",
    "_redact_sensitive",
    "get_audit_log_store",
    "get_last_hash",
    "log_event",
    "verify_hash_chain",
]
