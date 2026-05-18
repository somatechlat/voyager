"""ProjectBudget model for multi-type budget management.

Tracks budget consumption, forecasting, and alert thresholds for
fixed, hourly, retainer, and hybrid project types.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class ProjectBudget(TimestampedModel):
    """Budget allocation and tracking for a project."""

    class BudgetType(models.TextChoices):
        FIXED = "fixed", "Fixed Price"
        HOURLY = "hourly", "Hourly"
        RETAINER = "retainer", "Retainer"
        HYBRID = "hybrid", "Hybrid"

    class AlertLevel(models.TextChoices):
        NONE = "none", "None"
        LOW = "low", "50%"
        MEDIUM = "medium", "75%"
        HIGH = "high", "90%"
        CRITICAL = "critical", "100%"

    tenant_id = models.CharField(max_length=128, db_index=True, help_text="Tenant identifier")
    project = models.OneToOneField(
        "clients.Project",
        on_delete=models.CASCADE,
        related_name="budget_detail",
        help_text="The project this budget is for",
    )
    budget_type = models.CharField(
        max_length=20,
        choices=BudgetType.choices,
        default=BudgetType.FIXED,
        db_index=True,
        help_text="How the project is budgeted",
    )
    total_budget = models.DecimalField(
        max_digits=14, decimal_places=2, help_text="Total budget amount"
    )
    hours_allocated = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Hours allocated (for hourly/retainer types)",
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Hourly rate (for hourly/hybrid types)",
    )
    monthly_retainer = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Monthly retainer amount (for retainer type)",
    )
    base_retainer = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Base retainer (for hybrid type)",
    )
    overage_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Rate for hours beyond allocation",
    )
    budget_consumed = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Amount consumed so far",
    )
    hours_consumed = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Hours consumed so far",
    )
    alert_level = models.CharField(
        max_length=20,
        choices=AlertLevel.choices,
        default=AlertLevel.NONE,
        db_index=True,
        help_text="Current budget alert level",
    )
    alert_thresholds = models.JSONField(
        default=dict,
        help_text="Custom alert thresholds (JSON with pct -> level mapping)",
    )
    last_alert_sent_at = models.DateTimeField(
        blank=True, null=True, help_text="When the last alert was sent"
    )
    forecast_data = models.JSONField(
        blank=True, default=dict, help_text="Pre-computed forecast data"
    )
    start_date = models.DateField(help_text="Budget period start")
    end_date = models.DateField(blank=True, null=True, help_text="Budget period end")
    currency = models.CharField(max_length=3, default="USD", help_text="Currency code (ISO 4217)")

    class Meta:
        db_table = "voyager_project_budget"
        verbose_name = "Project Budget"
        verbose_name_plural = "Project Budgets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "budget_type", "alert_level"],
                name="voy_pb_tenant_type_alert_idx",
            ),
            models.Index(
                fields=["tenant_id", "start_date", "end_date"],
                name="voy_pb_tenant_date_range_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Budget for {self.project.name} ({self.budget_type})"
