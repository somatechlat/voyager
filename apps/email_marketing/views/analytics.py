"""Email analytics dashboard views."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.email_marketing.models.analytics import EmailAnalytics
from apps.email_marketing.models.campaign import EmailCampaign
from apps.email_marketing.serializers import (
    DeviceBreakdownSchema,
    EmailAnalyticsDetailSchema,
    EmailAnalyticsListSchema,
    EngagementTierSchema,
    HeatmapGenerateSchema,
    HourlyBreakdownSchema,
)
from apps.email_marketing.services.analytics import (
    aggregate_campaign_analytics,
    compute_device_breakdown,
    compute_engagement_tiers,
    generate_click_heatmap,
    get_campaign_hourly_breakdown,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/", response=list[EmailAnalyticsListSchema])
def list_analytics(
    request,
    tenant_id: str = "",
    campaign_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[EmailAnalytics]:
    """List email analytics records.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        campaign_id: Filter by campaign.
        limit: Page size.
        offset: Pagination offset.

    Returns:
        List of analytics records.
    """
    qs = EmailAnalytics.objects.select_related("campaign").all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if campaign_id:
        qs = qs.filter(campaign_id=campaign_id)
    return list(qs.order_by("-calculated_at")[offset : offset + limit])


@router.get("/{analytics_id}", response=EmailAnalyticsDetailSchema)
def get_analytics(
    request,
    analytics_id: int,
) -> EmailAnalytics:
    """Get analytics for a campaign.

    Args:
        request: HTTP request.
        analytics_id: Analytics primary key.

    Returns:
        Email analytics record.
    """
    return get_object_or_404(EmailAnalytics.objects.select_related("campaign"), id=analytics_id)


@router.post("/aggregate/{campaign_id}")
def aggregate_analytics(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Aggregate analytics for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.

    Returns:
        Aggregated analytics.
    """
    result = aggregate_campaign_analytics(campaign_id)
    return result


@router.post("/heatmap/{campaign_id}")
def heatmap(
    request,
    campaign_id: int,
    payload: HeatmapGenerateSchema,
) -> dict[str, Any]:
    """Generate click heatmap for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.
        payload: Heatmap generation data.

    Returns:
        Heatmap data.
    """
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    heatmap_data = generate_click_heatmap(
        blocks=payload.blocks,
        click_events=payload.click_events,
        total_delivered=payload.total_delivered or campaign.delivered or 1,
    )
    analytics, _ = EmailAnalytics.objects.get_or_create(
        campaign=campaign,
        defaults={"tenant_id": campaign.tenant_id},
    )
    analytics.click_heatmap = {"blocks": heatmap_data}
    analytics.calculated_at = datetime.now(UTC)
    analytics.save(update_fields=["click_heatmap", "calculated_at"])
    return {
        "campaign_id": str(campaign.id),
        "blocks": heatmap_data,
        "total_blocks": len(heatmap_data),
    }


@router.post("/engagement-tiers")
def engagement_tiers(
    request,
    payload: EngagementTierSchema,
) -> dict[str, Any]:
    """Compute engagement tier distribution.

    Args:
        request: HTTP request.
        payload: Tenant filter.

    Returns:
        Engagement tier distribution.
    """
    result = compute_engagement_tiers(
        tenant_id=payload.tenant_id,
    )
    return result


@router.post("/device-breakdown")
def device_breakdown(
    request,
    payload: DeviceBreakdownSchema,
) -> dict[str, Any]:
    """Compute device and platform breakdown.

    Args:
        request: HTTP request.
        payload: Device event data.

    Returns:
        Device breakdown.
    """
    result = compute_device_breakdown(
        tenant_id=payload.tenant_id,
        device_data=payload.device_data or None,
    )
    return result


@router.post("/hourly-breakdown/{campaign_id}")
def hourly_breakdown(
    request,
    campaign_id: int,
    payload: HourlyBreakdownSchema,
) -> dict[str, Any]:
    """Get hourly opens and clicks breakdown.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.
        payload: Event data.

    Returns:
        Hourly breakdown.
    """
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    result = get_campaign_hourly_breakdown(
        campaign_id=campaign_id,
        events=payload.events,
    )
    analytics, _ = EmailAnalytics.objects.get_or_create(
        campaign=campaign,
        defaults={"tenant_id": campaign.tenant_id},
    )
    analytics.hourly_opens = dict(enumerate(result["opens_by_hour"]))
    analytics.hourly_clicks = dict(enumerate(result["clicks_by_hour"]))
    analytics.calculated_at = datetime.now(UTC)
    analytics.save(update_fields=["hourly_opens", "hourly_clicks", "calculated_at"])
    return result


@router.get("/dashboard/{campaign_id}")
def analytics_dashboard(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Get full analytics dashboard for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.

    Returns:
        Full analytics dashboard data.
    """
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    analytics, _ = EmailAnalytics.objects.get_or_create(
        campaign=campaign,
        defaults={"tenant_id": campaign.tenant_id},
    )
    return {
        "campaign_id": str(campaign.id),
        "campaign_name": campaign.name,
        "sent": analytics.sent,
        "delivered": analytics.delivered,
        "delivery_rate": round(
            (analytics.delivered / analytics.sent * 100 if analytics.sent > 0 else 0.0), 2,
        ),
        "opens": analytics.opens,
        "unique_opens": analytics.unique_opens,
        "open_rate": analytics.open_rate,
        "clicks": analytics.clicks,
        "unique_clicks": analytics.unique_clicks,
        "click_rate": analytics.click_rate,
        "ctr": analytics.ctr,
        "bounces": analytics.bounces,
        "hard_bounces": analytics.hard_bounces,
        "bounce_rate": analytics.bounce_rate,
        "spam_complaints": analytics.spam_complaints,
        "unsubscribes": analytics.unsubscribes,
        "conversions": analytics.conversions,
        "conversion_rate": analytics.conversion_rate,
        "revenue": float(analytics.revenue),
        "revenue_per_email": analytics.revenue_per_email,
        "click_heatmap": analytics.click_heatmap,
        "device_breakdown": analytics.device_breakdown,
        "geographic_breakdown": analytics.geographic_breakdown,
        "hourly_opens": analytics.hourly_opens,
        "hourly_clicks": analytics.hourly_clicks,
        "engagement_tiers": analytics.engagement_tiers,
        "calculated_at": analytics.calculated_at.isoformat() if analytics.calculated_at else None,
    }
