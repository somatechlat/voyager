"""Audit middleware for Voyager.

Automatically logs all mutating HTTP requests (POST, PUT, PATCH, DELETE) to
the audit log with hash-chain integrity. Immutable by design — entries are
never updated or deleted after creation.

The hash chain links each entry to the previous one via SHA-256:
    hash[n] = SHA-256(hash[n-1] + canonical(entry[n]))

This ensures tamper-evidence: modifying any entry breaks the chain.
"""

from .hash_chain import verify_hash_chain
from .logging import _extract_action, _extract_resource, log_event
from .middleware import AuditMiddleware
from .redaction import SENSITIVE_KEYS, SKIP_PATHS, _redact_sensitive
from .storage import (
    _audit_log_store,
    _last_hash,
    get_audit_log_store,
    get_last_hash,
)

__all__ = [
    "AuditMiddleware",
    "SENSITIVE_KEYS",
    "SKIP_PATHS",
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
