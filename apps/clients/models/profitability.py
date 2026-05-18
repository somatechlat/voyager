"""ClientProfitability model."""

from __future__ import annotations

from django.db import models

from apps.clients.models.client import Client


class ClientProfitability(models.Model):
    """Profitability snapshot for a client over a time period.

    Attributes:
        id: Auto-incrementing primary key.
        tenant_id: Tenant identifier for multi-tenancy isolation.
        client: The client this profitability record is for.
        period_start: Start of the reporting period.
        period_end: End of the reporting period.
        revenue: Total revenue for the period.
        costs: Total costs for the period.
        margin_percent: Gross margin percentage.
        breakdown: JSON detailed breakdown of revenue and cost components.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """

    id = models.BigAutoField(primary_key=True, editable=False)
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="profitability_records",
        help_text="The client this profitability record is for",
    )
    period_start = models.DateField(help_text="Start of the reporting period")
    period_end = models.DateField(help_text="End of the reporting period")
    revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Total revenue for the period",
    )
    costs = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text="Total costs for the period",
    )
    margin_percent = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Gross margin percentage",
    )
    breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed breakdown of revenue and cost components",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        db_table = "voyager_client_profitability"
        verbose_name = "Client Profitability"
        verbose_name_plural = "Client Profitabilities"
        ordering = ["-period_end", "client"]
        indexes = [
            models.Index(fields=["tenant_id", "client", "period_end"]),
            models.Index(fields=["tenant_id", "period_start", "period_end"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "client", "period_start", "period_end"],
                name="clients_profit_period_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.client.name} ({self.period_start} to {self.period_end})"

    @property
    def gross_profit(self) -> float:
        """Calculate gross profit for the period.

        Returns:
            Gross profit (revenue minus costs) as a float.
        """
        return float(self.revenue) - float(self.costs)
