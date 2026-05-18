"""Brand safety model."""

from __future__ import annotations

from django.db import models


class BrandSafetyRule(models.Model):
    """Brand safety rule for content scanning.

    Stores configurable rules for profanity detection, sensitive topic
    filtering, competitor mention blocking, and custom pattern matching.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        name: Human-readable rule name.
        description: Optional explanation of the rule.
        rule_type: Category of brand safety check.
        conditions: JSON conditions dict (patterns, word lists, etc.).
        action: Response action when the rule triggers.
        severity: Severity level of violations from this rule.
        enabled: Whether the rule is active.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    class RuleType(models.TextChoices):
        """Supported brand safety rule types."""

        PROFANITY = "profanity", "Profanity Filter"
        SENSITIVE_TOPIC = "sensitive_topic", "Sensitive Topic Filter"
        COMPETITOR = "competitor", "Competitor Mention Filter"
        MEDICAL_CLAIM = "medical_claim", "Medical Claim Check"
        FINANCIAL_PROMISE = "financial_promise", "Financial Promise Check"
        DISCLAIMER = "disclaimer", "Required Disclaimer Check"
        CUSTOM = "custom", "Custom Rule"

    class Action(models.TextChoices):
        """Actions to take when a rule triggers."""

        BLOCK = "block", "Block"
        FLAG = "flag", "Flag for Review"
        WARN = "warn", "Warn Only"

    class Severity(models.TextChoices):
        """Severity levels for rule violations."""

        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    name = models.CharField(max_length=255, help_text="Human-readable rule name")
    description = models.TextField(
        blank=True, help_text="Optional explanation of the rule's purpose"
    )
    rule_type = models.CharField(
        max_length=32,
        choices=RuleType.choices,
        help_text="Category of brand safety check",
    )
    conditions = models.JSONField(
        default=dict, help_text="JSON conditions (patterns, word lists, thresholds)"
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        default=Action.FLAG,
        help_text="Response action when the rule triggers",
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.HIGH,
        help_text="Severity level of violations from this rule",
    )
    enabled = models.BooleanField(default=True, help_text="Whether the rule is active")
    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, db_index=True, help_text="Timestamp when the record was last updated"
    )

    class Meta:
        db_table = "voyager_brand_safety_rule"
        verbose_name = "Brand Safety Rule"
        verbose_name_plural = "Brand Safety Rules"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "rule_type", "enabled"]),
            models.Index(fields=["tenant_id", "severity", "enabled"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.rule_type})"
