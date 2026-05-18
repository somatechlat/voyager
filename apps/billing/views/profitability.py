"""Profitability views.

API endpoints for P&L reports, margin analysis, and trend data.
"""

from __future__ import annotations

from datetime import date

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.billing.models.profitability import ProfitabilityReport
from apps.billing.serializers import (
    ProfitabilityListSchema,
    ProfitabilitySchema,
    ProfitabilitySummarySchema,
)
from apps.billing.services.profitability import (
    compute_client_profitability,
    generate_profitability_summary,
)
from apps.rbac.auth import VoyagerKeycloakBearer

router = Router(auth=VoyagerKeycloakBearer())


@router.get("/profitability", response=list[ProfitabilityListSchema], tags=["Billing"])
def list_profitability_reports(
    request,
    dimension: str | None = None,
    dimension_id: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    is_current: bool | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List profitability reports with filtering."""
    tenant_id = getattr(request, "tenant_id", "")
    qs = ProfitabilityReport.objects.filter(tenant_id=tenant_id)
    if dimension:
        qs = qs.filter(dimension=dimension)
    if dimension_id:
        qs = qs.filter(dimension_id=dimension_id)
    if period_start:
        qs = qs.filter(period_start__gte=period_start)
    if period_end:
        qs = qs.filter(period_end__lte=period_end)
    if is_current is not None:
        qs = qs.filter(is_current=is_current)
    return list(qs.order_by("-period_end")[offset : offset + limit])


@router.get("/profitability/{int:report_id}", response=ProfitabilitySchema, tags=["Billing"])
def get_profitability_report(request, report_id: int):
    """Get a profitability report."""
    tenant_id = getattr(request, "tenant_id", "")
    return get_object_or_404(ProfitabilityReport, tenant_id=tenant_id, pk=report_id)


@router.post("/profitability/compute", response=ProfitabilitySchema, tags=["Billing"])
def compute_profitability(
    request,
    client_id: int,
    dimension: str = "client",
    period_start: date | None = None,
    period_end: date | None = None,
):
    """Compute a profitability report for a client and period."""
    tenant_id = getattr(request, "tenant_id", "")
    today = date.today()
    if period_start is None:
        period_start = today.replace(day=1)
    if period_end is None:
        period_end = today
    report = compute_client_profitability(tenant_id, client_id, dimension, period_start, period_end)
    return report


@router.get(
    "/profitability/summary",
    response=ProfitabilitySummarySchema,
    tags=["Billing"],
)
def get_profitability_summary(
    request,
    dimension: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
):
    """Get summary across profitability reports."""
    tenant_id = getattr(request, "tenant_id", "")
    qs = ProfitabilityReport.objects.filter(tenant_id=tenant_id)
    if dimension:
        qs = qs.filter(dimension=dimension)
    if period_start:
        qs = qs.filter(period_start__gte=period_start)
    if period_end:
        qs = qs.filter(period_end__lte=period_end)
    reports = list(qs)
    return generate_profitability_summary(reports)
