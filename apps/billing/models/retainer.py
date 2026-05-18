"""Retainer model for retainer agreement management.

Tracks retainer contracts with monthly allocations, auto-renewal,
rollover policies, consumption alerts, and overage billing.
"""

from __future__ import annotations

from django.db import models

from .base import TimestampedModel


class Retainer(TimestampedModel):
    """A retainer agreement with a client."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        PAUSED = "paused", "Paused"
        PENDING = "pending", "Pending"

    class RenewalType(models.TextChoices):
        AUTO = "auto", "Auto-Renew"
        MANUAL = "manual", "Manual"
        FIXED_TERM = "fixed_term", "Fixed Term"

    tenant_id = models.CharField(max_length=128, db_index=True, help_text="Tenant identifier")
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.CASCADE,
        related_name="retainers",
        help_text="The client this retainer is for",
    )
    name = models.CharField(max_length=255, help_text="Retainer agreement name")
    monthly_amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Monthly retainer amount"
    )
    monthly_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Hours included per month",
    )
    start_date = models.DateField(help_text="Retainer start date")
    end_date = models.DateField(
        blank=True, null=True, help_text="Retainer end date (null = ongoing)"
    )
    renewal_type = models.CharField(
        max_length=20,
        choices=RenewalType.choices,
        default=RenewalType.AUTO,
        help_text="How the retainer renews",
    )
    renewal_term_months = models.PositiveIntegerField(
        default=12, help_text="Renewal term in months"
    )
    auto_invoice = models.BooleanField(default=True, help_text="Auto-generate monthly invoice")
    invoice_day = models.PositiveIntegerField(
        default=1, help_text="Day of month to generate invoice"
    )
    rollover_policy = models.JSONField(
        default=dict,
        help_text="Rollover rules: {type, maxRolloverHours, maxRolloverMonths, expiration}",
    )
    overage_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Hourly rate for overage hours",
    )
    overage_billing_threshold = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Minimum overage hours before billing",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text="Retainer status",
    )
    currency = models.CharField(max_length=3, default="USD", help_text="Currency code")
    consumption_alert_thresholds = models.JSONField(
        default=list,
        help_text="Alert thresholds: [75, 90, 100]",
    )
    last_invoiced_month = models.DateField(
        blank=True, null=True, help_text="Last month that was invoiced"
    )
    total_hours_consumed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, help_text="Total hours consumed"
    )
    total_amount_invoiced = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Total amount invoiced"
    )
    notes = models.TextField(blank=True, help_text="Internal notes")
    contract_url = models.URLField(blank=True, default="", help_text="Link to contract document")
    metadata = models.JSONField(blank=True, default=dict, help_text="Extensible metadata")

    class Meta:
        db_table = "voyager_retainer"
        verbose_name = "Retainer"
        verbose_name_plural = "Retainers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "client", "status"],
                name="voy_ret_tenant_client_status_idx",
            ),
            models.Index(
                fields=["tenant_id", "status", "start_date"],
                name="voy_ret_tenant_status_start_idx",
            ),
            models.Index(
                fields=["tenant_id", "auto_invoice", "status"],
                name="voy_ret_tenant_auto_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} - {self.client.name}"
