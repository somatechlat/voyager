"""Client profitability service.

Handles P&L calculations, margin analysis, and profitability
snapshot creation for clients over defined time periods.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.db.models import QuerySet, Sum
from ninja.errors import HttpError

from apps.clients.models.client import Client
from apps.clients.models.profitability import ClientProfitability
from apps.clients.models.project import Project

logger = logging.getLogger(__name__)


class ProfitabilityService:
    """Service for client profitability analysis.

    Provides CRUD for profitability records, margin calculations,
    and period-over-period comparisons.
    """

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def create(tenant_id: str, client_id: int, data: dict[str, Any]) -> ClientProfitability:
        """Create a profitability record for a client.

        Args:
            tenant_id: The tenant identifier.
            client_id: The client primary key.
            data: Dictionary of profitability field values.

        Returns:
            The newly created ClientProfitability instance.

        Raises:
            HttpError: 404 if the client does not exist.
        """
        try:
            client = Client.objects.get(tenant_id=tenant_id, id=client_id)
        except Client.DoesNotExist:
            raise HttpError(404, "Client not found")

        revenue = Decimal(data.get("revenue", "0.00"))
        costs = Decimal(data.get("costs", "0.00"))
        if revenue > 0:
            margin_percent = ((revenue - costs) / revenue) * Decimal("100")
        else:
            margin_percent = Decimal("0.00")

        data["revenue"] = revenue
        data["costs"] = costs
        data["margin_percent"] = margin_percent

        record = ClientProfitability.objects.create(
            tenant_id=tenant_id,
            client=client,
            **data,
        )
        logger.info(
            "Profitability record created for client %s: margin=%s%%",
            client.name,
            margin_percent,
        )
        return record

    @staticmethod
    def list_records(
        tenant_id: str,
        client_id: int | None = None,
    ) -> QuerySet[ClientProfitability]:
        """List profitability records with optional client filter.

        Args:
            tenant_id: The tenant identifier.
            client_id: Optional client filter.

        Returns:
            QuerySet of matching ClientProfitability instances.
        """
        qs: QuerySet[ClientProfitability] = ClientProfitability.objects.filter(tenant_id=tenant_id)
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs.order_by("-period_end")

    @staticmethod
    def get_by_id(tenant_id: str, record_id: int) -> ClientProfitability:
        """Retrieve a profitability record by ID.

        Args:
            tenant_id: The tenant identifier.
            record_id: The record primary key.

        Returns:
            The ClientProfitability instance.

        Raises:
            HttpError: 404 if the record does not exist.
        """
        try:
            return ClientProfitability.objects.get(tenant_id=tenant_id, id=record_id)
        except ClientProfitability.DoesNotExist:
            raise HttpError(404, "Profitability record not found")

    @staticmethod
    def update(record: ClientProfitability, data: dict[str, Any]) -> ClientProfitability:
        """Update a profitability record.

        Recalculates margin_percent if revenue or costs are updated.

        Args:
            record: The ClientProfitability instance.
            data: Dictionary of fields to update.

        Returns:
            The updated ClientProfitability instance.
        """
        for key, value in data.items():
            if value is not None and hasattr(record, key):
                setattr(record, key, value)

        # Recalculate margin if revenue or costs changed
        revenue = Decimal(record.revenue)
        costs = Decimal(record.costs)
        if revenue > 0:
            record.margin_percent = ((revenue - costs) / revenue) * Decimal("100")
        else:
            record.margin_percent = Decimal("0.00")

        record.save()
        logger.info("Profitability record updated: %s", record.id)
        return record

    @staticmethod
    def delete(record: ClientProfitability) -> None:
        """Delete a profitability record.

        Args:
            record: The ClientProfitability instance to delete.
        """
        record_id = record.id
        record.delete()
        logger.info("Profitability record deleted: %s", record_id)

    # ------------------------------------------------------------------
    # Calculations
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_from_projects(
        tenant_id: str,
        client_id: int,
        period_start: str,
        period_end: str,
    ) -> dict[str, Any]:
        """Calculate profitability from project data.

        Aggregates project budgets and costs to produce a profitability
        snapshot. This is a simplified calculation; real implementations
        would integrate with time tracking and invoicing systems.

        Args:
            tenant_id: The tenant identifier.
            client_id: The client primary key.
            period_start: Start date string (YYYY-MM-DD).
            period_end: End date string (YYYY-MM-DD).

        Returns:
            Dictionary with calculated profitability metrics.

        Raises:
            HttpError: 404 if the client does not exist.
        """
        try:
            client = Client.objects.get(tenant_id=tenant_id, id=client_id)
        except Client.DoesNotExist:
            raise HttpError(404, "Client not found")

        projects = Project.objects.filter(
            tenant_id=tenant_id,
            client=client,
            start_date__lte=period_end,
        )

        total_budget = projects.aggregate(total=Sum("budget_amount"))["total"] or Decimal("0.00")

        # Simplified cost model: 60% of budget as estimated cost
        estimated_costs = total_budget * Decimal("0.60")
        overhead = total_budget * Decimal("0.20")
        total_costs = estimated_costs + overhead

        if total_budget > 0:
            margin_percent = ((total_budget - total_costs) / total_budget) * Decimal("100")
            gross_profit = total_budget - total_costs
        else:
            margin_percent = Decimal("0.00")
            gross_profit = Decimal("0.00")

        breakdown: dict[str, Any] = {
            "revenue_sources": {
                "retainer": Decimal("0.00"),
                "project": total_budget,
                "hourly": Decimal("0.00"),
            },
            "cost_breakdown": {
                "labor": estimated_costs,
                "tools": Decimal("0.00"),
                "ad_spend": Decimal("0.00"),
                "overhead": overhead,
            },
            "project_count": projects.count(),
            "active_projects": projects.filter(status=Project.Status.ACTIVE).count(),
        }

        logger.info(
            "Profitability calculated for client %s: margin=%s%%",
            client.name,
            margin_percent,
        )

        return {
            "client_id": client_id,
            "period_start": period_start,
            "period_end": period_end,
            "revenue": total_budget,
            "costs": total_costs,
            "gross_profit": gross_profit,
            "margin_percent": round(margin_percent, 2),
            "breakdown": breakdown,
        }

    @staticmethod
    def get_client_summary(tenant_id: str, client_id: int) -> dict[str, Any]:
        """Get a summary of profitability across all periods for a client.

        Args:
            tenant_id: The tenant identifier.
            client_id: The client primary key.

        Returns:
            Dictionary with aggregated profitability metrics.
        """
        records = ClientProfitability.objects.filter(tenant_id=tenant_id, client_id=client_id)

        total_revenue = Decimal("0.00")
        total_costs = Decimal("0.00")
        for record in records:
            total_revenue += Decimal(record.revenue)
            total_costs += Decimal(record.costs)

        if total_revenue > 0:
            overall_margin = ((total_revenue - total_costs) / total_revenue) * Decimal("100")
        else:
            overall_margin = Decimal("0.00")

        return {
            "client_id": client_id,
            "period_count": records.count(),
            "total_revenue": total_revenue,
            "total_costs": total_costs,
            "gross_profit": total_revenue - total_costs,
            "overall_margin_percent": round(overall_margin, 2),
            "latest_record": records.first(),
        }
