"""Profitability analysis service.

Handles P&L calculation, margin tracking, benchmarking,
and profitability reporting across dimensions.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from apps.billing.models.invoice import Invoice
from apps.billing.models.profitability import ProfitabilityReport
from apps.billing.models.time_entry import TimeEntry

DIMENSIONS = [
    "client",
    "project",
    "service",
    "team_member",
    "channel",
    "month",
    "quarter",
]


def calculate_gross_margin(revenue: Decimal, total_costs: Decimal) -> Decimal:
    """Calculate gross margin percentage.

    Args:
        revenue: Total revenue.
        total_costs: Total costs.

    Returns:
        Gross margin as a percentage.
    """
    if revenue <= 0:
        return Decimal("0")
    return Decimal(str(round(((revenue - total_costs) / revenue) * 100, 2)))


def calculate_trend(monthly_values: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate month-over-month trend.

    Args:
        monthly_values: List of {month, value} dicts.

    Returns:
        Dict with direction, change_pct.
    """
    if len(monthly_values) < 2:
        return {"direction": "flat", "change_pct": Decimal("0")}
    current = Decimal(str(monthly_values[-1].get("value", 0)))
    previous = Decimal(str(monthly_values[-2].get("value", 0)))
    if previous <= 0:
        return {"direction": "flat", "change_pct": Decimal("0")}
    change_pct = Decimal(str(round(((current - previous) / previous) * 100, 2)))
    direction = "up" if change_pct > 0 else "down" if change_pct < 0 else "flat"
    return {"direction": direction, "change_pct": change_pct}


def compute_client_profitability(
    tenant_id: str,
    client_id: int,
    dimension: str,
    period_start: date,
    period_end: date,
) -> ProfitabilityReport | None:
    """Compute or update a profitability report.

    Aggregates revenue from invoices, costs from time entries and
    expenses for the given dimension and period.

    Args:
        tenant_id: Tenant identifier.
        client_id: Client ID.
        dimension: Analysis dimension.
        period_start: Period start date.
        period_end: Period end date.

    Returns:
        ProfitabilityReport instance or None.
    """
    invoices = Invoice.objects.filter(
        tenant_id=tenant_id,
        client_id=client_id,
        status=Invoice.Status.PAID,
        invoice_date__gte=period_start,
        invoice_date__lte=period_end,
    )
    revenue = Decimal("0")
    for inv in invoices:
        revenue += Decimal(str(inv.total))
    time_entries = TimeEntry.objects.filter(
        tenant_id=tenant_id,
        client_id=client_id,
        started_at__date__gte=period_start,
        started_at__date__lte=period_end,
    )
    labor_cost = Decimal("0")
    hours_logged = Decimal("0")
    for te in time_entries:
        rate = te.billing_rate or Decimal("0")
        hours = Decimal(str(te.duration_minutes)) / Decimal("60")
        labor_cost += hours * rate
        hours_logged += hours
    total_cost = labor_cost
    gross_profit = revenue - total_cost
    gross_margin = calculate_gross_margin(revenue, total_cost)
    effective_rate = Decimal(str(round(revenue / hours_logged, 2))) if hours_logged > 0 else None
    report, _created = ProfitabilityReport.objects.update_or_create(
        tenant_id=tenant_id,
        dimension=dimension,
        dimension_id=str(client_id),
        period_start=period_start,
        period_end=period_end,
        defaults={
            "dimension_name": f"Client {client_id}",
            "revenue": revenue,
            "labor_cost": labor_cost,
            "tool_cost": Decimal("0"),
            "expense_cost": Decimal("0"),
            "overhead_cost": Decimal("0"),
            "total_cost": total_cost,
            "gross_profit": gross_profit,
            "gross_margin_pct": gross_margin,
            "hours_logged": hours_logged,
            "effective_hourly_rate": effective_rate,
            "breakdown": {
                "invoice_count": invoices.count(),
                "time_entry_count": time_entries.count(),
            },
            "status": ProfitabilityReport.Status.FINAL,
            "is_current": True,
        },
    )
    ProfitabilityReport.objects.filter(
        tenant_id=tenant_id,
        dimension=dimension,
        dimension_id=str(client_id),
    ).exclude(pk=report.pk).update(is_current=False)
    return report


def generate_profitability_summary(
    reports: list[ProfitabilityReport],
) -> dict[str, Any]:
    """Generate a summary across multiple profitability reports.

    Args:
        reports: List of ProfitabilityReport instances.

    Returns:
        Dict with aggregated totals and averages.
    """
    total_revenue = Decimal("0")
    total_cost = Decimal("0")
    total_profit = Decimal("0")
    for r in reports:
        total_revenue += r.revenue
        total_cost += r.total_cost
        total_profit += r.gross_profit
    avg_margin = (
        Decimal(str(round((total_profit / total_revenue) * 100, 2)))
        if total_revenue > 0
        else Decimal("0")
    )
    return {
        "total_revenue": str(total_revenue),
        "total_cost": str(total_cost),
        "total_profit": str(total_profit),
        "avg_margin_pct": str(avg_margin),
        "report_count": len(reports),
    }
