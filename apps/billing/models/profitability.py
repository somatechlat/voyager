"""ProfitabilityReport model for P&L analysis.

Tracks revenue, costs, and margins by project, client, team,
or other dimensions for financial reporting.
"""

from __future__ import annotations

from django.db import models

from .base import TimestampedModel


class ProfitabilityReport(TimestampedModel):
    """Pre-computed profitability report for a dimension and period."""

    class Dimension(models.TextChoices):
        CLIENT = "client", "Client"
        PROJECT = "project", "Project"
        SERVICE = "service", "Service"
        TEAM_MEMBER = "team_member", "Team Member"
        CHANNEL = "channel", "Channel"
        MONTH = "month", "Month"
        QUARTER = "quarter", "Quarter"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINAL = "final", "Final"
        ARCHIVED = "archived", "Archived"

    tenant_id = models.CharField(max_length=128, db_index=True, help_text="Tenant identifier")
    dimension = models.CharField(
        max_length=20,
        choices=Dimension.choices,
        db_index=True,
        help_text="Analysis dimension",
    )
    dimension_id = models.CharField(
        max_length=128, db_index=True, help_text="ID of the entity being analyzed"
    )
    dimension_name = models.CharField(max_length=255, help_text="Human-readable name")
    period_start = models.DateField(db_index=True, help_text="Start of reporting period")
    period_end = models.DateField(db_index=True, help_text="End of reporting period")
    revenue = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Total revenue"
    )
    labor_cost = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Labor costs"
    )
    tool_cost = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Tool/subscription costs"
    )
    expense_cost = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Expense costs"
    )
    overhead_cost = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Overhead allocation"
    )
    total_cost = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Sum of all costs"
    )
    gross_profit = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, help_text="Revenue - total cost"
    )
    gross_margin_pct = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Gross margin percentage",
    )
    benchmark_margin_pct = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Benchmark margin for comparison",
    )
    margin_vs_benchmark = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Difference from benchmark",
    )
    breakdown = models.JSONField(blank=True, default=dict, help_text="Detailed P&L breakdown")
    trend_data = models.JSONField(blank=True, default=dict, help_text="Month-over-month trend")
    hours_billed = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, help_text="Total hours billed"
    )
    hours_logged = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, help_text="Total hours logged"
    )
    effective_hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Average effective hourly rate",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Report status",
    )
    is_current = models.BooleanField(
        default=True, db_index=True, help_text="Whether this is the current report"
    )

    class Meta:
        db_table = "voyager_profitability_report"
        verbose_name = "Profitability Report"
        verbose_name_plural = "Profitability Reports"
        ordering = ["-period_end", "dimension", "-gross_margin_pct"]
        indexes = [
            models.Index(
                fields=["tenant_id", "dimension", "dimension_id", "period_end"],
                name="voy_pr_tenant_dim_id_period_idx",
            ),
            models.Index(
                fields=["tenant_id", "period_start", "period_end"],
                name="voy_pr_tenant_period_range_idx",
            ),
            models.Index(
                fields=["tenant_id", "dimension", "-gross_margin_pct"],
                name="voy_pr_tenant_dim_margin_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "dimension", "dimension_id", "period_start", "period_end"],
                name="voyager_pr_unique_period",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.dimension_name} ({self.period_start} to {self.period_end})"
