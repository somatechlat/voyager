"""Campaign performance and dashboard views.

Performance aggregation, time series, dashboard KPIs, and ROI endpoints.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.campaigns.models import Campaign, CampaignPerformance
from apps.campaigns.serializers import (
    DashboardKPIsSchema,
    PerformanceRecordSchema,
    ROISchema,
)
from apps.campaigns.services.performance import (
    calculate_roi,
    get_campaign_summary,
    get_channel_performance,
    get_dashboard_kpis,
    get_time_series,
)

logger = logging.getLogger(__name__)

router = Router()


@router.post("/{campaign_id}/performance")
def record_performance(
    request,
    campaign_id: int,
    payload: PerformanceRecordSchema,
) -> dict[str, Any]:
    """Record daily performance metrics.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        payload: Performance data.

    Returns:
        Created record.
    """
    perf, created = CampaignPerformance.objects.update_or_create(
        campaign_id=campaign_id,
        channel_id=payload.channel_id,
        metric_date=payload.metric_date,
        defaults={
            "impressions": payload.impressions,
            "clicks": payload.clicks,
            "conversions": payload.conversions,
            "spend": payload.spend,
            "revenue": payload.revenue,
            "engagement_actions": payload.engagement_actions,
            "metrics": payload.metrics,
        },
    )

    return {
        "success": True,
        "record_id": perf.id,
        "created": created,
        "metric_date": payload.metric_date.isoformat(),
    }


@router.get("/{campaign_id}/performance/summary")
def performance_summary(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Get performance summary for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Summary dict.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return get_campaign_summary(campaign)


@router.get("/{campaign_id}/performance/channels")
def performance_channels(
    request,
    campaign_id: int,
) -> list[dict[str, Any]]:
    """Get performance by channel.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Channel performance list.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return get_channel_performance(campaign)


@router.get("/{campaign_id}/performance/timeseries")
def performance_timeseries(
    request,
    campaign_id: int,
    start_date: str = "",
    end_date: str = "",
    granularity: str = "daily",
) -> list[dict[str, Any]]:
    """Get time-series performance data.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        start_date: ISO date string.
        end_date: ISO date string.
        granularity: 'daily' or 'hourly'.

    Returns:
        Time series data.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)

    start: date | None = None
    end: date | None = None
    if start_date:
        start = date.fromisoformat(start_date)
    if end_date:
        end = date.fromisoformat(end_date)

    return get_time_series(campaign, start_date=start, end_date=end, granularity=granularity)


@router.get("/{campaign_id}/dashboard", response=DashboardKPIsSchema)
def dashboard(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Get dashboard KPIs for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Dashboard KPI dict.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return get_dashboard_kpis(campaign)


@router.post("/{campaign_id}/roi")
def roi_calculation(
    request,
    campaign_id: int,
    payload: ROISchema,
) -> dict[str, Any]:
    """Calculate campaign ROI.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        payload: Cost parameters.

    Returns:
        ROI calculation.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return calculate_roi(
        campaign=campaign,
        labor_cost=payload.labor_cost,
        tool_costs=payload.tool_costs,
        overhead_pct=payload.overhead_pct,
    )


@router.get("/{campaign_id}/performance/comparison")
def performance_comparison(
    request,
    campaign_id: int,
    compare_with: str = "",
) -> dict[str, Any]:
    """Compare campaign performance against another campaign or benchmark.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        compare_with: Other campaign ID or 'industry_average'.

    Returns:
        Comparison result.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    current = get_campaign_summary(campaign)

    if compare_with == "industry_average":
        benchmark = {
            "ctr": 2.5,
            "conversion_rate": 3.0,
            "cpa": 35.0,
            "roas": 3.5,
        }
    elif compare_with and compare_with.isdigit():
        other = get_object_or_404(Campaign, id=int(compare_with))
        benchmark = get_campaign_summary(other)
    else:
        benchmark = {}

    return {
        "campaign": current,
        "benchmark": benchmark,
        "comparison": {
            "ctr_delta": (
                current["ctr"] - benchmark["ctr"] if benchmark and "ctr" in benchmark else None
            ),
            "conversion_rate_delta": (
                current["conversion_rate"] - benchmark["conversion_rate"]
                if benchmark and "conversion_rate" in benchmark
                else None
            ),
            "roas_delta": (
                current["roas"] - benchmark["roas"] if benchmark and "roas" in benchmark else None
            ),
        },
    }
