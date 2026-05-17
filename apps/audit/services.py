"""Audit logging service for immutable audit trail management.

Provides the ``AuditService`` class with static methods for creating
audit log entries, querying logs, and exporting audit trails. All
operations maintain the SHA-256 hash chain for tamper evidence.
"""

from __future__ import annotations

import csv
import gzip
import json
import logging
from datetime import datetime
from io import StringIO
from typing import Any

from django.db import transaction
from django.db.models import QuerySet

from apps.audit.models import AuditLogArchive, AuditLogEntry

logger = logging.getLogger(__name__)


class AuditService:
    """Service class for audit logging operations.

    All methods are static and operate on the ``AuditLogEntry`` and
    ``AuditLogArchive`` models. The hash chain is automatically
    maintained by :meth:`log` which fetches the previous entry's
    hash before computing the current entry's hash.
    """

    @staticmethod
    def log(
        *,
        tenant_id: str,
        actor_id: str,
        actor_type: str,
        action: str,
        resource_type: str,
        resource_id: str,
        outcome: str,
        actor_email: str = "",
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str = "",
        request_id: str = "",
        session_id: str = "",
    ) -> AuditLogEntry:
        """Create a new audit log entry with automatic hash chaining.

        Retrieves the previous hash for the tenant, computes the SHA-256
        hash for the new entry, and persists it atomically.

        Args:
            tenant_id: Tenant identifier for multi-tenancy isolation.
            actor_id: Keycloak subject identifier of the actor.
            actor_type: Kind of actor (user, service, agent).
            action: The action performed (e.g. ``"content.created"``).
            resource_type: Category of the affected resource.
            resource_id: Identifier of the affected resource.
            outcome: Result of the action (success, failure, denied).
            actor_email: Optional email address of the actor.
            details: Optional JSON payload with before/after values.
            ip_address: Optional IP address of the actor.
            user_agent: Optional HTTP user agent string.
            request_id: Optional correlation ID for distributed tracing.
            session_id: Optional session identifier.

        Returns:
            The created ``AuditLogEntry`` instance.

        Raises:
            ValueError: If actor_type or outcome is not a valid choice.
        """
        # Validate choice fields
        valid_actor_types = {c[0] for c in AuditLogEntry.ActorType.choices}
        valid_outcomes = {c[0] for c in AuditLogEntry.Outcome.choices}

        if actor_type not in valid_actor_types:
            raise ValueError(
                f"Invalid actor_type '{actor_type}'. " f"Must be one of: {valid_actor_types}"
            )
        if outcome not in valid_outcomes:
            raise ValueError(f"Invalid outcome '{outcome}'. " f"Must be one of: {valid_outcomes}")

        previous_hash = AuditService.get_previous_hash(tenant_id)

        entry = AuditLogEntry(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            previous_hash=previous_hash,
            entry_hash="",  # Computed after save when timestamp is set
        )

        with transaction.atomic():
            entry.save()
            entry.entry_hash = entry.compute_hash()
            entry.save(update_fields=["entry_hash"])

        logger.debug(
            "Audit log created: %s by %s on %s:%s -> %s (hash: %s...)",
            action,
            actor_id,
            resource_type,
            resource_id,
            outcome,
            entry.entry_hash[:16],
        )

        return entry

    @staticmethod
    def get_previous_hash(tenant_id: str) -> str:
        """Retrieve the hash of the most recent audit log entry for a tenant.

        Used by :meth:`log` to maintain the SHA-256 hash chain.

        Args:
            tenant_id: The tenant identifier to look up.

        Returns:
            The ``entry_hash`` of the most recent entry, or an empty
            string if the tenant has no prior entries.
        """
        try:
            latest = (
                AuditLogEntry.objects.filter(
                    tenant_id=tenant_id,
                )
                .order_by("-timestamp")
                .first()
            )
            return latest.entry_hash if latest else ""
        except Exception:
            return ""

    @staticmethod
    def query_logs(
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLogEntry]:
        """Query audit log entries for a tenant with optional filters.

        Args:
            tenant_id: The tenant identifier to scope the query.
            filters: Optional filter dictionary. Supported keys:
                - ``actor_id``: Filter by actor.
                - ``actor_type``: Filter by actor type.
                - ``action``: Filter by action (supports ``action__icontains``).
                - ``resource_type``: Filter by resource type.
                - ``resource_id``: Filter by resource ID.
                - ``outcome``: Filter by outcome.
                - ``start_date``: Datetime for ``timestamp__gte``.
                - ``end_date``: Datetime for ``timestamp__lte``.
                - ``request_id``: Filter by request/correlation ID.
            limit: Maximum number of entries to return.
            offset: Number of entries to skip.

        Returns:
            List of ``AuditLogEntry`` instances ordered by descending timestamp.
        """
        filters = filters or {}
        qs: QuerySet[AuditLogEntry] = AuditLogEntry.objects.filter(
            tenant_id=tenant_id,
        )

        if actor_id := filters.get("actor_id"):
            qs = qs.filter(actor_id=actor_id)
        if actor_type := filters.get("actor_type"):
            qs = qs.filter(actor_type=actor_type)
        if action := filters.get("action"):
            qs = qs.filter(action__icontains=action)
        if resource_type := filters.get("resource_type"):
            qs = qs.filter(resource_type=resource_type)
        if resource_id := filters.get("resource_id"):
            qs = qs.filter(resource_id=resource_id)
        if outcome := filters.get("outcome"):
            qs = qs.filter(outcome=outcome)
        if request_id := filters.get("request_id"):
            qs = qs.filter(request_id=request_id)
        if start_date := filters.get("start_date"):
            qs = qs.filter(timestamp__gte=start_date)
        if end_date := filters.get("end_date"):
            qs = qs.filter(timestamp__lte=end_date)

        return list(qs.order_by("-timestamp")[offset : offset + limit])

    @staticmethod
    def query_logs_count(tenant_id: str, filters: dict[str, Any] | None = None) -> int:
        """Return the total count of audit log entries matching the filters.

        Args:
            tenant_id: The tenant identifier to scope the query.
            filters: Optional filter dictionary (same keys as :meth:`query_logs`).

        Returns:
            Total number of matching entries.
        """
        filters = filters or {}
        qs: QuerySet[AuditLogEntry] = AuditLogEntry.objects.filter(tenant_id=tenant_id)

        if actor_id := filters.get("actor_id"):
            qs = qs.filter(actor_id=actor_id)
        if actor_type := filters.get("actor_type"):
            qs = qs.filter(actor_type=actor_type)
        if action := filters.get("action"):
            qs = qs.filter(action__icontains=action)
        if resource_type := filters.get("resource_type"):
            qs = qs.filter(resource_type=resource_type)
        if resource_id := filters.get("resource_id"):
            qs = qs.filter(resource_id=resource_id)
        if outcome := filters.get("outcome"):
            qs = qs.filter(outcome=outcome)
        if request_id := filters.get("request_id"):
            qs = qs.filter(request_id=request_id)
        if start_date := filters.get("start_date"):
            qs = qs.filter(timestamp__gte=start_date)
        if end_date := filters.get("end_date"):
            qs = qs.filter(timestamp__lte=end_date)

        return qs.count()

    @staticmethod
    def export_logs(
        tenant_id: str,
        export_format: str = "csv",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> str:
        """Export audit log entries for a tenant in the requested format.

        Args:
            tenant_id: The tenant identifier to scope the export.
            export_format: Output format -- ``"csv"`` or ``"json"``.
            start_date: Optional start of the date range (inclusive).
            end_date: Optional end of the date range (inclusive).

        Returns:
            The exported data as a string (CSV or JSON).

        Raises:
            ValueError: If an unsupported export format is requested.
        """
        qs: QuerySet[AuditLogEntry] = AuditLogEntry.objects.filter(
            tenant_id=tenant_id,
        )
        if start_date:
            qs = qs.filter(timestamp__gte=start_date)
        if end_date:
            qs = qs.filter(timestamp__lte=end_date)

        entries = qs.order_by("-timestamp")

        if export_format == "csv":
            return AuditService._export_csv(entries)
        elif export_format == "json":
            return AuditService._export_json(entries)
        else:
            raise ValueError(
                f"Unsupported export format '{export_format}'. " "Use 'csv' or 'json'."
            )

    @staticmethod
    def _export_csv(entries: QuerySet[AuditLogEntry]) -> str:
        """Convert audit log entries to CSV format.

        Args:
            entries: QuerySet of ``AuditLogEntry`` instances.

        Returns:
            CSV-formatted string with header row.
        """
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "timestamp",
                "tenant_id",
                "actor_id",
                "actor_type",
                "actor_email",
                "action",
                "resource_type",
                "resource_id",
                "outcome",
                "details",
                "ip_address",
                "user_agent",
                "request_id",
                "session_id",
                "previous_hash",
                "entry_hash",
            ]
        )
        for entry in entries.iterator():
            writer.writerow(
                [
                    entry.timestamp.isoformat(),
                    entry.tenant_id,
                    entry.actor_id,
                    entry.actor_type,
                    entry.actor_email,
                    entry.action,
                    entry.resource_type,
                    entry.resource_id,
                    entry.outcome,
                    json.dumps(entry.details),
                    entry.ip_address or "",
                    entry.user_agent,
                    entry.request_id,
                    entry.session_id,
                    entry.previous_hash,
                    entry.entry_hash,
                ]
            )
        return output.getvalue()

    @staticmethod
    def _export_json(entries: QuerySet[AuditLogEntry]) -> str:
        """Convert audit log entries to JSON format.

        Args:
            entries: QuerySet of ``AuditLogEntry`` instances.

        Returns:
            JSON-formatted string with a list of log entry objects.
        """
        results: list[dict[str, Any]] = []
        for entry in entries.iterator():
            results.append(
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "tenant_id": entry.tenant_id,
                    "actor_id": entry.actor_id,
                    "actor_type": entry.actor_type,
                    "actor_email": entry.actor_email,
                    "action": entry.action,
                    "resource_type": entry.resource_type,
                    "resource_id": entry.resource_id,
                    "outcome": entry.outcome,
                    "details": entry.details,
                    "ip_address": entry.ip_address,
                    "user_agent": entry.user_agent,
                    "request_id": entry.request_id,
                    "session_id": entry.session_id,
                    "previous_hash": entry.previous_hash,
                    "entry_hash": entry.entry_hash,
                }
            )
        return json.dumps(results, indent=2, default=str)

    @staticmethod
    def archive_logs(
        tenant_id: str,
        year_month: str,
    ) -> AuditLogArchive:
        """Archive audit log entries for a tenant and month.

        Compresses all matching entries into a binary JSON payload
        stored in ``AuditLogArchive``. The original entries may be
        purged after successful archiving.

        Args:
            tenant_id: The tenant identifier to scope the archive.
            year_month: Month in ``YYYY-MM`` format.

        Returns:
            The created ``AuditLogArchive`` instance.

        Raises:
            ValueError: If ``year_month`` is not in ``YYYY-MM`` format.
        """
        if len(year_month) != 7 or year_month[4] != "-":
            raise ValueError("year_month must be in YYYY-MM format")

        start_dt = datetime.strptime(year_month, "%Y-%m")
        if start_dt.month == 12:
            end_dt = datetime(start_dt.year + 1, 1, 1)
        else:
            end_dt = datetime(start_dt.year, start_dt.month + 1, 1)

        entries = AuditLogEntry.objects.filter(
            tenant_id=tenant_id,
            timestamp__gte=start_dt,
            timestamp__lt=end_dt,
        ).order_by("timestamp")

        log_data: list[dict[str, Any]] = []
        count = 0
        for entry in entries.iterator():
            log_data.append(
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "tenant_id": entry.tenant_id,
                    "actor_id": entry.actor_id,
                    "actor_type": entry.actor_type,
                    "actor_email": entry.actor_email,
                    "action": entry.action,
                    "resource_type": entry.resource_type,
                    "resource_id": entry.resource_id,
                    "outcome": entry.outcome,
                    "details": entry.details,
                    "ip_address": entry.ip_address,
                    "user_agent": entry.user_agent,
                    "request_id": entry.request_id,
                    "session_id": entry.session_id,
                    "previous_hash": entry.previous_hash,
                    "entry_hash": entry.entry_hash,
                }
            )
            count += 1

        compressed = gzip.compress(
            json.dumps(log_data, default=str).encode("utf-8"),
            compresslevel=6,
        )

        archive, _ = AuditLogArchive.objects.update_or_create(
            tenant_id=tenant_id,
            year_month=year_month,
            defaults={
                "log_count": count,
                "archive_data": compressed,
            },
        )

        logger.info(
            "Archived %d audit log entries for tenant=%s month=%s " "(compressed: %d bytes)",
            count,
            tenant_id,
            year_month,
            len(compressed),
        )

        return archive

    @staticmethod
    def verify_chain_integrity(tenant_id: str, limit: int = 1000) -> dict[str, Any]:
        """Verify the hash chain integrity for a tenant's recent audit logs.

        Walks the entries in reverse chronological order and checks
        that each entry's ``previous_hash`` matches the next entry's
        ``entry_hash``.

        Args:
            tenant_id: The tenant identifier to verify.
            limit: Maximum number of recent entries to check.

        Returns:
            Dictionary with ``valid`` (bool), ``checked`` (int), and
            ``first_broken_id`` (int or None) keys.
        """
        entries = list(
            AuditLogEntry.objects.filter(tenant_id=tenant_id).order_by("-timestamp")[:limit]
        )

        if len(entries) < 2:
            return {"valid": True, "checked": len(entries), "first_broken_id": None}

        for i in range(len(entries) - 1):
            current = entries[i]
            next_entry = entries[i + 1]

            if not current.verify_hash():
                return {
                    "valid": False,
                    "checked": i + 1,
                    "first_broken_id": current.id,
                }

            if current.previous_hash != next_entry.entry_hash:
                return {
                    "valid": False,
                    "checked": i + 1,
                    "first_broken_id": current.id,
                }

        return {"valid": True, "checked": len(entries), "first_broken_id": None}
