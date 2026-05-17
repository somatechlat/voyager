"""Hash chain computation and verification for audit log integrity."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from .storage import _audit_log_store

logger = logging.getLogger(__name__)


def _canonical_json(data: dict[str, Any]) -> str:
    """Create a deterministic JSON representation for hashing.

    Sorts keys recursively to ensure the same data always produces the
    same canonical string regardless of insertion order.

    Args:
        data: Dictionary to serialise.

    Returns:
        Deterministic JSON string with sorted keys.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def _compute_hash(previous_hash: str, entry_data: dict[str, Any]) -> str:
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


def verify_hash_chain(tenant_id: str | None = None) -> dict[str, Any]:
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
            "checked_at": datetime.now(UTC),
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
                "checked_at": datetime.now(UTC),
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
        "checked_at": datetime.now(UTC),
    }
