"""In-memory audit log storage and append operations."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# In-memory audit log storage — replaced by database-backed model in production.
# Protected by module-level access only; no external modification allowed.
_audit_log_store: list[dict[str, Any]] = []
_last_hash: str = "0" * 64  # Genesis hash


def _generate_entry_id() -> str:
    """Generate a unique entry identifier.

    Returns:
        UUID4 string.
    """
    import uuid

    return str(uuid.uuid4())


def _append_audit_entry(entry: dict[str, Any]) -> str:
    """Append an entry to the audit log with hash-chain integrity.

    This is the ONLY function that writes to ``_audit_log_store``.

    Args:
        entry: Audit entry dictionary (without hash field).

    Returns:
        The computed hash for the entry.
    """
    global _last_hash

    from .hash_chain import _compute_hash

    # Compute hash covering previous hash + entry content
    entry_hash = _compute_hash(_last_hash, entry)

    entry["previous_hash"] = _last_hash
    entry["hash"] = entry_hash
    entry["id"] = str(entry.get("id", _generate_entry_id()))

    _audit_log_store.append(entry)
    _last_hash = entry_hash

    return entry_hash


def get_audit_log_store() -> list[dict[str, Any]]:
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
