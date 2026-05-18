"""Data sync engine: bidirectional sync, conflict resolution, delta sync.

Supports field mapping, diff detection, multiple conflict resolution
strategies (source-wins, target-wins, last-write-wins, manual), and
scheduling for periodic sync operations.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from django.utils import timezone

from apps.integrations.models import PlatformConnection, SyncLog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FieldMapping:
    """Maps a source field to a target field with optional transform."""

    source: str
    target: str
    transform: str | None = None


@dataclass
class SyncConfig:
    """Configuration for a sync operation."""

    connection_id: str
    sync_type: str
    direction: str = "bidirectional"
    conflict_resolution: str = "source_wins"
    field_mappings: list[FieldMapping] = field(default_factory=list)
    match_field: str = "id"
    delete_propagation: bool = False
    source_data: list[dict[str, Any]] = field(default_factory=list)
    target_data: list[dict[str, Any]] = field(default_factory=list)
    transform_rules: dict[str, str] = field(default_factory=dict)


@dataclass
class SyncResult:
    """Result of a sync operation."""

    created: int = 0
    updated: int = 0
    deleted: int = 0
    conflicts: int = 0
    unchanged: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "updated": self.updated,
            "deleted": self.deleted,
            "conflicts": self.conflicts,
            "unchanged": self.unchanged,
            "total_changes": self.created + self.updated + self.deleted + self.conflicts,
        }


# ---------------------------------------------------------------------------
# Conflict resolution strategies
# ---------------------------------------------------------------------------


class ConflictResolver:
    """Applies conflict resolution strategies between source and target records."""

    STRATEGIES = {"source_wins", "target_wins", "last_write_wins", "manual"}

    @classmethod
    def resolve(
        cls,
        source: dict[str, Any],
        target: dict[str, Any],
        strategy: str,
        source_updated: str | None = None,
        target_updated: str | None = None,
    ) -> dict[str, Any] | None:
        """Resolve a conflict between two records.

        Args:
            source: The source-side record.
            target: The target-side record.
            strategy: Resolution strategy name.
            source_updated: ISO timestamp of last source update.
            target_updated: ISO timestamp of last target update.

        Returns:
            The winning record, or None for ``manual`` strategy.
        """
        if strategy not in cls.STRATEGIES:
            strategy = "source_wins"

        if strategy == "source_wins":
            return source
        elif strategy == "target_wins":
            return target
        elif strategy == "last_write_wins":
            if source_updated and target_updated:
                if source_updated >= target_updated:
                    return source
                return target
            return source
        elif strategy == "manual":
            return None
        return source


# ---------------------------------------------------------------------------
# Field mapping and transforms
# ---------------------------------------------------------------------------


def apply_field_mapping(record: dict[str, Any], mappings: list[FieldMapping]) -> dict[str, Any]:
    """Map source fields to target fields for a single record.

    Args:
        record: The source record.
        mappings: List of FieldMapping rules.

    Returns:
        A new record with fields remapped according to the rules.
    """
    mapped: dict[str, Any] = {}
    for m in mappings:
        value = record.get(m.source)
        if value is not None:
            if m.transform == "uppercase":
                value = str(value).upper()
            elif m.transform == "lowercase":
                value = str(value).lower()
            elif m.transform == "strip":
                value = str(value).strip()
        mapped[m.target] = value
    return mapped


def compute_record_hash(record: dict[str, Any]) -> str:
    """Compute a stable hash of a record for change detection.

    Args:
        record: The record to hash.

    Returns:
        SHA-256 hex digest of the canonical JSON representation.
    """
    canonical = json.dumps(record, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Diff engine
# ---------------------------------------------------------------------------


@dataclass
class Change:
    """A single change detected between source and target datasets."""

    change_type: str  # create, update, delete, conflict
    match_value: str
    source_record: dict[str, Any] | None = None
    target_record: dict[str, Any] | None = None
    resolved_record: dict[str, Any] | None = None


def compute_diff(
    source_data: list[dict[str, Any]],
    target_data: list[dict[str, Any]],
    match_field: str = "id",
    conflict_resolution: str = "source_wins",
    source_timestamps: dict[str, str] | None = None,
    target_timestamps: dict[str, str] | None = None,
) -> list[Change]:
    """Compute the diff between source and target datasets.

    Args:
        source_data: Records from the source system.
        target_data: Records from the target system.
        match_field: Field used to match records across datasets.
        conflict_resolution: Strategy for handling conflicts.
        source_timestamps: Map of match_value -> ISO timestamp.
        target_timestamps: Map of match_value -> ISO timestamp.

    Returns:
        List of Change objects describing all detected changes.
    """
    source_index: dict[str, dict[str, Any]] = {}
    for rec in source_data:
        key = str(rec.get(match_field, ""))
        if key:
            source_index[key] = rec

    target_index: dict[str, dict[str, Any]] = {}
    for rec in target_data:
        key = str(rec.get(match_field, ""))
        if key:
            target_index[key] = rec

    changes: list[Change] = []
    all_keys = set(source_index.keys()) | set(target_index.keys())

    for key in all_keys:
        src = source_index.get(key)
        tgt = target_index.get(key)

        if src and not tgt:
            changes.append(Change("create", key, source_record=src))
        elif tgt and not src:
            changes.append(Change("delete", key, target_record=tgt))
        elif src and tgt:
            src_hash = compute_record_hash(src)
            tgt_hash = compute_record_hash(tgt)
            if src_hash != tgt_hash:
                resolved = ConflictResolver.resolve(
                    src,
                    tgt,
                    conflict_resolution,
                    source_timestamps.get(key) if source_timestamps else None,
                    target_timestamps.get(key) if target_timestamps else None,
                )
                if resolved is None:
                    changes.append(Change("conflict", key, source_record=src, target_record=tgt))
                else:
                    changes.append(
                        Change(
                            "update",
                            key,
                            source_record=src,
                            target_record=tgt,
                            resolved_record=resolved,
                        )
                    )

    return changes


# ---------------------------------------------------------------------------
# Sync execution
# ---------------------------------------------------------------------------


def run_sync(config: SyncConfig) -> SyncResult:
    """Execute a full sync operation.

    Maps fields, computes diffs, applies changes, and logs the result.

    Args:
        config: The sync configuration.

    Returns:
        SyncResult with counts of changes applied.
    """
    result = SyncResult()

    # Apply field mappings to source data
    mapped_source = [
        apply_field_mapping(rec, config.field_mappings) if config.field_mappings else rec
        for rec in config.source_data
    ]

    # Compute diff
    changes = compute_diff(
        mapped_source,
        config.target_data,
        match_field=config.match_field,
        conflict_resolution=config.conflict_resolution,
    )

    # Apply changes
    for change in changes:
        if change.change_type == "create":
            result.created += 1
        elif change.change_type == "update":
            result.updated += 1
        elif change.change_type == "delete" and config.delete_propagation:
            result.deleted += 1
        elif change.change_type == "conflict":
            result.conflicts += 1

    return result


def run_sync_for_connection(
    connection: PlatformConnection,
    sync_type: str,
    direction: str = "inbound",
    conflict_resolution: str = "source_wins",
    field_mappings_json: list[dict[str, Any]] | None = None,
    source_data: list[dict[str, Any]] | None = None,
    target_data: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run a sync operation for a connection and persist the result.

    Creates a SyncLog entry and returns the sync results.

    Args:
        connection: The platform connection.
        sync_type: Type of sync (e.g. ``"contacts"``, ``"products"``).
        direction: Data flow direction.
        conflict_resolution: Conflict resolution strategy.
        field_mappings_json: JSON-serializable field mappings.
        source_data: Source dataset records.
        target_data: Target dataset records.

    Returns:
        Dictionary with sync results and the sync log ID.
    """
    log = SyncLog.objects.create(
        connection=connection,
        sync_type=sync_type,
        direction=direction,
        status=SyncLog.Status.RUNNING,
        conflict_resolution=conflict_resolution,
        field_mappings_json=field_mappings_json or [],
        started_at=timezone.now(),
    )

    try:
        mappings = [
            FieldMapping(m["source"], m["target"], m.get("transform"))
            for m in (field_mappings_json or [])
        ]

        config = SyncConfig(
            connection_id=str(connection.id),
            sync_type=sync_type,
            direction=direction,
            conflict_resolution=conflict_resolution,
            field_mappings=mappings,
            source_data=source_data or [],
            target_data=target_data or [],
        )

        result = run_sync(config)

        log.status = SyncLog.Status.PARTIAL if result.conflicts else SyncLog.Status.COMPLETED
        log.records_count = result.created + result.updated + result.deleted
        log.created_count = result.created
        log.updated_count = result.updated
        log.deleted_count = result.deleted
        log.conflict_count = result.conflicts
        log.errors_json = result.errors
        log.completed_at = timezone.now()
        log.save()

        return {
            "success": True,
            "sync_log_id": str(log.id),
            **result.to_dict(),
        }

    except Exception as exc:
        log.status = SyncLog.Status.FAILED
        log.errors_json = [{"error": str(exc)}]
        log.completed_at = timezone.now()
        log.save()
        logger.exception("Sync failed for connection %s: %s", connection.id, exc)
        return {
            "success": False,
            "sync_log_id": str(log.id),
            "error": str(exc),
            "created": 0,
            "updated": 0,
            "deleted": 0,
            "conflicts": 0,
            "unchanged": 0,
            "total_changes": 0,
        }


# ---------------------------------------------------------------------------
# Delta sync helpers
# ---------------------------------------------------------------------------


def compute_delta(
    new_data: list[dict[str, Any]],
    previous_data: list[dict[str, Any]],
    match_field: str = "id",
) -> dict[str, Any]:
    """Compute delta changes between a previous and current dataset snapshot.

    Args:
        new_data: Current dataset.
        previous_data: Previous dataset snapshot.
        match_field: Field used to match records.

    Returns:
        Dictionary with ``added``, ``modified``, ``removed`` lists.
    """
    prev_index = {str(r.get(match_field, "")): r for r in previous_data}
    new_index = {str(r.get(match_field, "")): r for r in new_data}

    added: list[dict[str, Any]] = []
    modified: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []

    for key, rec in new_index.items():
        if key not in prev_index:
            added.append(rec)
        elif compute_record_hash(rec) != compute_record_hash(prev_index[key]):
            modified.append(rec)

    for key, rec in prev_index.items():
        if key not in new_index:
            removed.append(rec)

    return {
        "added": added,
        "modified": modified,
        "removed": removed,
        "added_count": len(added),
        "modified_count": len(modified),
        "removed_count": len(removed),
    }
