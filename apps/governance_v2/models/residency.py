"""Data residency and cross-border transfer models."""

from __future__ import annotations

from django.db import models


class DataResidencyConfig(models.Model):
    """Data residency configuration per tenant.

    Enforces where data is stored and which cross-border transfers
    are permitted for compliance with GDPR, CCPA, and other regulations.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier (unique, one config per tenant).
        primary_region: Primary data storage region code.
        allowed_regions: JSON list of permitted region codes.
        data_types: JSON map of data categories to their residency rules.
        restriction_level: Restriction classification.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    class RestrictionLevel(models.TextChoices):
        """Levels of data residency restriction."""

        STANDARD = "standard", "Standard"
        RESTRICTED = "restricted", "Restricted"
        STRICT = "strict", "Strict (No Cross-Border)"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="Tenant identifier (unique, one config per tenant)",
    )
    primary_region = models.CharField(
        max_length=50, help_text="Primary data storage region code (e.g. 'eu-west-1')"
    )
    allowed_regions = models.JSONField(
        default=list, help_text="JSON list of permitted region codes"
    )
    data_types = models.JSONField(
        default=dict, blank=True, help_text="JSON map of data categories to residency rules"
    )
    restriction_level = models.CharField(
        max_length=20,
        choices=RestrictionLevel.choices,
        default=RestrictionLevel.STANDARD,
        help_text="Restriction classification for data transfers",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, db_index=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        db_table = "voyager_data_residency_config"
        verbose_name = "Data Residency Config"
        verbose_name_plural = "Data Residency Configs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "primary_region"]),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_id} -> {self.primary_region}"


class CrossBorderTransfer(models.Model):
    """Log of cross-border data transfer attempts.

    Records each attempted transfer of data across regional boundaries
    for compliance auditing and breach investigation.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        data_type: Category of data being transferred.
        source_region: Origin region code.
        target_region: Destination region code.
        status: Result of the transfer check.
        reason: Human-readable explanation of the decision.
        created_at: Timestamp when the record was created.
    """

    class Status(models.TextChoices):
        """Outcome of a cross-border transfer request."""

        ALLOWED = "allowed", "Allowed"
        BLOCKED = "blocked", "Blocked"
        LOGGED = "logged", "Logged"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    data_type = models.CharField(max_length=50, help_text="Category of data being transferred")
    source_region = models.CharField(max_length=50, help_text="Origin region code")
    target_region = models.CharField(max_length=50, help_text="Destination region code")
    status = models.CharField(
        max_length=20, choices=Status.choices, help_text="Result of the transfer check"
    )
    reason = models.TextField(blank=True, help_text="Human-readable explanation of the decision")
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the record was created"
    )

    class Meta:
        db_table = "voyager_cross_border_transfer"
        verbose_name = "Cross-Border Transfer"
        verbose_name_plural = "Cross-Border Transfers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "source_region", "target_region"]),
            models.Index(fields=["tenant_id", "status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_region} -> {self.target_region} ({self.status})"
