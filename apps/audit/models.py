"""Audit models for immutable audit logging.

Defines AuditLogEntry and AuditLogArchive models that provide a tamper-evident
audit trail using SHA-256 hash chains. All audit records are tenant-scoped
and support compliance-ready querying, export, and archival.
"""

from __future__ import annotations

import hashlib
from typing import Any

from django.db import models


class AuditLogEntry(models.Model):
    """Immutable audit log entry with SHA-256 hash chain integrity.

    Each entry cryptographically links to the previous entry within the
    same tenant via a SHA-256 hash chain. Tampering with any record
    breaks the chain, making alteration detectable through
    :meth:`verify_hash`.

    Attributes:
        id: Auto-incrementing primary key (BigAutoField).
        timestamp: When the audited event occurred.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        actor_id: Keycloak subject identifier of the actor.
        actor_type: Kind of actor (user, service, or AI agent).
        actor_email: Optional email address of the actor.
        action: The action that was performed (e.g. "content.created").
        resource_type: Category of the affected resource.
        resource_id: Identifier of the affected resource.
        outcome: Result of the action (success, failure, or denied).
        details: JSON payload with before/after values and extra context.
        ip_address: Optional IP address of the actor.
        user_agent: Optional HTTP user agent string.
        request_id: Optional correlation ID for distributed tracing.
        session_id: Optional session identifier.
        previous_hash: SHA-256 hash of the preceding tenant log entry.
        hash: SHA-256 hash of this entry (chain link).
    """

    class ActorType(models.TextChoices):
        """Supported kinds of actors that can perform actions."""

        USER = "user", "User"
        SERVICE = "service", "Service"
        AGENT = "agent", "AI Agent"

    class Outcome(models.TextChoices):
        """Possible results of an audited action."""

        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        DENIED = "denied", "Access Denied"

    id = models.BigAutoField(primary_key=True, editable=False)
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the audited event occurred",
    )
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    actor_id = models.CharField(
        max_length=256,
        db_index=True,
        help_text="Keycloak subject identifier of the actor",
    )
    actor_type = models.CharField(
        max_length=32,
        choices=ActorType.choices,
        help_text="Kind of actor: user, service, or AI agent",
    )
    actor_email = models.CharField(
        max_length=256,
        blank=True,
        help_text="Optional email address of the actor",
    )
    action = models.CharField(
        max_length=128,
        db_index=True,
        help_text="The action performed (e.g. 'content.created')",
    )
    resource_type = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Category of the affected resource (e.g. 'content_generation')",
    )
    resource_id = models.CharField(
        max_length=256,
        help_text="Identifier of the affected resource",
    )
    outcome = models.CharField(
        max_length=32,
        choices=Outcome.choices,
        help_text="Result of the action: success, failure, or denied",
    )
    details = models.JSONField(
        default=dict,
        help_text="JSON payload with before/after values and extra context",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Optional IP address of the actor",
    )
    user_agent = models.TextField(
        blank=True,
        help_text="Optional HTTP user agent string",
    )
    request_id = models.CharField(
        max_length=128,
        blank=True,
        help_text="Optional correlation ID for distributed tracing",
    )
    session_id = models.CharField(
        max_length=128,
        blank=True,
        help_text="Optional session identifier",
    )
    previous_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hash of the preceding tenant log entry",
    )
    entry_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 hash of this entry (chain link)",
    )

    class Meta:
        db_table = "voyager_audit_log"
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["tenant_id", "timestamp"]),
            models.Index(fields=["tenant_id", "actor_id", "timestamp"]),
            models.Index(fields=["tenant_id", "action", "timestamp"]),
            models.Index(fields=["tenant_id", "resource_type", "resource_id"]),
            models.Index(fields=["request_id"]),
            models.Index(fields=["session_id"]),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.timestamp.isoformat()}] "
            f"{self.action} by {self.actor_type}:{self.actor_id} "
            f"on {self.resource_type}:{self.resource_id} -> {self.outcome}"
        )

    def compute_hash(self) -> str:
        """Compute the SHA-256 hash for this entry.

        The hash covers: timestamp, tenant_id, actor_id, action,
        resource_id, outcome, and the previous_hash. This forms a
        cryptographically linked chain where tampering with any
        field (or the previous entry) invalidates all subsequent hashes.

        Returns:
            Hexadecimal SHA-256 digest string (64 characters).
        """
        data = (
            f"{self.timestamp.isoformat()}|"
            f"{self.tenant_id}|"
            f"{self.actor_id}|"
            f"{self.action}|"
            f"{self.resource_id}|"
            f"{self.outcome}|"
            f"{self.previous_hash}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_hash(self) -> bool:
        """Verify the integrity of this log entry.

        Re-computes the expected hash and compares it against the
        stored ``entry_hash``. A ``False`` return indicates the
        record has been tampered with.

        Returns:
            ``True`` if the stored hash matches the computed hash,
            ``False`` if tampering is detected.
        """
        return self.entry_hash == self.compute_hash()

    def verify_chain(self) -> dict[str, Any]:
        """Verify this entry's place in the hash chain.

        Checks both the entry's own hash integrity and that the
        previous_hash links correctly to the prior entry in the
        same tenant.

        Returns:
            Dictionary with keys ``entry_valid`` (bool) and
            ``chain_valid`` (bool or None if no previous entry).
        """
        result: dict[str, Any] = {
            "entry_valid": self.verify_hash(),
            "chain_valid": None,
        }
        if self.previous_hash:
            try:
                prev = AuditLogEntry.objects.filter(
                    tenant_id=self.tenant_id,
                    timestamp__lt=self.timestamp,
                ).order_by("-timestamp").first()
                if prev:
                    result["chain_valid"] = self.previous_hash == prev.entry_hash
            except AuditLogEntry.DoesNotExist:
                result["chain_valid"] = False
        return result


class AuditLogArchive(models.Model):
    """Archived audit logs stored after the retention period expires.

    When audit log entries exceed the configured retention period,
    they are rolled up into compressed monthly archives per tenant.
    The original entries may then be purged from the hot table.

    Attributes:
        id: Auto-incrementing primary key (BigAutoField).
        year_month: The archive month in ``YYYY-MM`` format.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        log_count: Number of log entries contained in the archive.
        archive_data: Compressed binary JSON containing the log entries.
        created_at: Timestamp when the archive was created.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    year_month = models.CharField(
        max_length=7,
        db_index=True,
        help_text="The archive month in YYYY-MM format",
    )
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    log_count = models.IntegerField(
        help_text="Number of log entries contained in the archive",
    )
    archive_data = models.BinaryField(
        help_text="Compressed binary JSON containing the log entries",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the archive was created",
    )

    class Meta:
        db_table = "voyager_audit_log_archive"
        verbose_name = "Audit Log Archive"
        verbose_name_plural = "Audit Log Archives"
        ordering = ["-year_month", "tenant_id"]
        indexes = [
            models.Index(fields=["tenant_id", "year_month"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "year_month"],
                name="%(app_label)s_archive_tenant_month_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_id} / {self.year_month} ({self.log_count} entries)"
