"""Compliance rule model."""

from __future__ import annotations

from django.db import models


class ComplianceRule(models.Model):
    """Industry-specific compliance rule template.

    Stores regulatory rules for FDA (healthcare), FINRA (finance),
    FTC (advertising), COPPA (children's content), and custom regulations.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        industry: Target industry sector.
        regulation: Regulation code (e.g. "FDA 21 CFR 202").
        name: Human-readable rule name.
        description: Detailed explanation of the requirement.
        check_type: Mechanism used to validate compliance.
        check_config: JSON configuration for the check.
        severity: Severity level of violations.
        legal_reference: Citation to the legal text.
        remediation: Steps to resolve a violation.
        enabled: Whether the rule is active.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    class Industry(models.TextChoices):
        """Supported industry sectors."""

        HEALTHCARE = "healthcare", "Healthcare"
        FINANCE = "finance", "Finance"
        ADVERTISING = "advertising", "Advertising"
        CHILDREN = "children", "Children's Content"
        ALCOHOL = "alcohol", "Alcohol"
        CANNABIS = "cannabis", "Cannabis"
        GENERAL = "general", "General"

    class Severity(models.TextChoices):
        """Severity levels for compliance violations."""

        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128, db_index=True, help_text="Tenant identifier for multi-tenancy isolation"
    )
    industry = models.CharField(
        max_length=32, choices=Industry.choices, help_text="Target industry sector"
    )
    regulation = models.CharField(
        max_length=100, help_text="Regulation code (e.g. 'FDA 21 CFR 202')"
    )
    name = models.CharField(max_length=255, help_text="Human-readable rule name")
    description = models.TextField(blank=True, help_text="Detailed explanation of the requirement")
    check_type = models.CharField(
        blank=True, max_length=50, help_text="Mechanism used to validate compliance"
    )
    check_config = models.JSONField(
        blank=True, default=dict, help_text="JSON configuration for the compliance check"
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.HIGH,
        help_text="Severity level of violations",
    )
    legal_reference = models.TextField(blank=True, help_text="Citation to the legal text")
    remediation = models.TextField(blank=True, help_text="Steps to resolve a violation")
    enabled = models.BooleanField(default=True, help_text="Whether the rule is active")
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, db_index=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        db_table = "voyager_compliance_rule"
        verbose_name = "Compliance Rule"
        verbose_name_plural = "Compliance Rules"
        ordering = ["industry", "regulation", "name"]
        indexes = [
            models.Index(fields=["tenant_id", "industry", "enabled"]),
            models.Index(fields=["tenant_id", "regulation", "enabled"]),
            models.Index(fields=["tenant_id", "severity", "enabled"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.industry} / {self.regulation})"
