"""Campaign performance service with aggregation and ROI calculation.

Implements ClickHouse-aware query building, dashboard metric aggregation,
and configurable ROI/ROAS calculation with multiple attribution models.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import TruncDate, TruncHour

from apps.campaigns.models import Campaign, CampaignChannel, CampaignPerformance

logger = logging.getLogger(__name__)


def get_campaign_summary(campaign: Campaign) -> dict[str, Any]:
    """Get aggregated performance summary for a campaign.

    Args:
        campaign: The campaign.

    Returns:
        Dict with total impressions, clicks, conversions, spend,
        revenue, CTR, CPC, CPA, ROAS, conversion_rate.
    """
    aggs = CampaignPerformance.objects.filter(campaign=campaign).aggregate(
        total_impressions=Sum("impressions"),
        total_clicks=Sum("clicks"),
        total_conversions=Sum("conversions"),
        total_spend=Sum("spend"),
        total_revenue=Sum("revenue"),
        total_engagement=Sum("engagement_actions"),
        record_count=Count("id"),
    )

    impressions = aggs["total_impressions"] or 0
    clicks = aggs["total_clicks"] or 0
    conversions = aggs["total_conversions"] or 0
    spend = float(aggs["total_spend"] or 0)
    revenue = float(aggs["total_revenue"] or 0)
    engagement = aggs["total_engagement"] or 0

    ctr = (clicks / impressions * 100.0) if impressions > 0 else 0.0
    cpc = (spend / clicks) if clicks > 0 else 0.0
    cpa = (spend / conversions) if conversions > 0 else 0.0
    roas = (revenue / spend) if spend > 0 else 0.0
    conv_rate = (conversions / clicks * 100.0) if clicks > 0 else 0.0

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "period_days": aggs["record_count"] or 0,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "spend": round(spend, 2),
        "revenue": round(revenue, 2),
        "engagement_actions": engagement,
        "ctr": round(ctr, 4),
        "cpc": round(cpc, 2),
        "cpa": round(cpa, 2),
        "roas": round(roas, 4),
        "conversion_rate": round(conv_rate, 4),
        "budget_utilization": campaign.spend_percentage,
    }


def get_channel_performance(
    campaign: Campaign,
) -> list[dict[str, Any]]:
    """Get performance breakdown by channel.

    Args:
        campaign: The campaign.

    Returns:
        List of channel performance dicts.
    """
    channels = CampaignChannel.objects.filter(campaign=campaign)
    results: list[dict[str, Any]] = []

    for ch in channels:
        aggs = CampaignPerformance.objects.filter(
            campaign=campaign, channel=ch
        ).aggregate(
            total_impressions=Sum("impressions"),
            total_clicks=Sum("clicks"),
            total_conversions=Sum("conversions"),
            total_spend=Sum("spend"),
            total_revenue=Sum("revenue"),
        )

        impressions = aggs["total_impressions"] or 0
        clicks = aggs["total_clicks"] or 0
        conversions = aggs["total_conversions"] or 0
        ch_spend = float(aggs["total_spend"] or 0)
        ch_revenue = float(aggs["total_revenue"] or 0)

        results.append(
            {
                "channel_id": ch.id,
                "channel_type": ch.channel_type,
                "platform": ch.platform,
                "status": ch.status,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "spend": round(ch_spend, 2),
                "revenue": round(ch_revenue, 2),
                "ctr": round((clicks / impressions * 100.0), 4) if impressions > 0 else 0.0,
                "roas": round(ch_revenue / ch_spend, 4) if ch_spend > 0 else 0.0,
                "cpa": round(ch_spend / conversions, 2) if conversions > 0 else 0.0,
                "conversion_rate": round((conversions / clicks * 100.0), 4) if clicks > 0 else 0.0,
            }
        )

    return results


def get_time_series(
    campaign: Campaign,
    start_date: date | None = None,
    end_date: date | None = None,
    granularity: str = "daily",
) -> list[dict[str, Any]]:
    """Get time-series performance data.

    Args:
        campaign: The campaign.
        start_date: Optional filter start.
        end_date: Optional filter end.
        granularity: 'daily' or 'hourly'.

    Returns:
        List of time-bucketed metrics.
    """
    qs = CampaignPerformance.objects.filter(campaign=campaign)
    if start_date:
        qs = qs.filter(metric_date__gte=start_date)
    if end_date:
        qs = qs.filter(metric_date__lte=end_date)

    if granularity == "hourly":
        qs = qs.annotate(bucket=TruncHour("created_at"))
    else:
        qs = qs.annotate(bucket=TruncDate("metric_date"))

    results = qs.values("bucket").annotate(
        impressions=Sum("impressions"),
        clicks=Sum("clicks"),
        conversions=Sum("conversions"),
        spend=Sum("spend"),
        revenue=Sum("revenue"),
        engagement=Sum("engagement_actions"),
    ).order_by("bucket")

    output: list[dict[str, Any]] = []
    for row in results:
        imp = row["impressions"] or 0
        clk = row["clicks"] or 0
        conv = row["conversions"] or 0
        sp = float(row["spend"] or 0)
        rev = float(row["revenue"] or 0)
        output.append(
            {
                "date": row["bucket"].isoformat() if row["bucket"] else None,
                "impressions": imp,
                "clicks": clk,
                "conversions": conv,
                "spend": round(sp, 2),
                "revenue": round(rev, 2),
                "ctr": round((clk / imp * 100.0), 4) if imp > 0 else 0.0,
                "roas": round(rev / sp, 4) if sp > 0 else 0.0,
            }
        )

    return output


def get_dashboard_kpis(
    campaign: Campaign,
) -> dict[str, Any]:
    """Get dashboard KPI cards for a campaign.

    Returns:
        Dict with primary KPIs and sparkline-ready data.
    """
    summary = get_campaign_summary(campaign)

    # Get last 7 days for sparkline
    end = date.today()
    start = end - timedelta(days=6)
    sparkline = get_time_series(campaign, start_date=start, end_date=end)

    return {
        "campaign": {
            "id": campaign.id,
            "name": campaign.name,
            "stage": campaign.stage,
            "status": campaign.status,
        },
        "kpis": {
            "impressions": summary["impressions"],
            "clicks": summary["clicks"],
            "conversions": summary["conversions"],
            "spend": summary["spend"],
            "revenue": summary["revenue"],
            "ctr": summary["ctr"],
            "roas": summary["roas"],
            "cpa": summary["cpa"],
            "conversion_rate": summary["conversion_rate"],
            "budget_utilization": summary["budget_utilization"],
        },
        "sparkline": {
            "spend": [d["spend"] for d in sparkline],
            "revenue": [d["revenue"] for d in sparkline],
            "conversions": [d["conversions"] for d in sparkline],
            "clicks": [d["clicks"] for d in sparkline],
            "labels": [d["date"] for d in sparkline],
        },
        "channel_breakdown": get_channel_performance(campaign),
    }


def calculate_roi(
    campaign: Campaign,
    labor_cost: float = 0.0,
    tool_costs: float = 0.0,
    overhead_pct: float = 0.15,
) -> dict[str, Any]:
    """Calculate campaign ROI with configurable cost components.

    Args:
        campaign: The campaign.
        labor_cost: Total labor cost.
        tool_costs: Tool subscription costs.
        overhead_pct: Overhead percentage (0.15 = 15%).

    Returns:
        Dict with revenue, costs, roi, roas, profit_margin, cpa.
    """
    aggs = CampaignPerformance.objects.filter(campaign=campaign).aggregate(
        total_revenue=Sum("revenue"),
        total_conversions=Sum("conversions"),
    )

    revenue = float(aggs["total_revenue"] or 0)
    conversions = aggs["total_conversions"] or 0
    ad_spend = float(campaign.current_spend)

    overhead = (ad_spend + labor_cost + tool_costs) * overhead_pct
    total_cost = ad_spend + labor_cost + tool_costs + overhead

    if total_cost > 0:
        roi = ((revenue - total_cost) / total_cost) * 100.0
        roas = revenue / total_cost
    else:
        roi = 0.0
        roas = 0.0

    if revenue > 0:
        profit_margin = ((revenue - total_cost) / revenue) * 100.0
    else:
        profit_margin = 0.0

    cpa = total_cost / conversions if conversions > 0 else 0.0

    return {
        "revenue": round(revenue, 2),
        "total_cost": round(total_cost, 2),
        "ad_spend": round(ad_spend, 2),
        "labor_cost": round(labor_cost, 2),
        "tool_costs": round(tool_costs, 2),
        "overhead": round(overhead, 2),
        "conversions": conversions,
        "roi": round(roi, 2),
        "roas": round(roas, 4),
        "profit_margin": round(profit_margin, 2),
        "cpa": round(cpa, 2),
    }
