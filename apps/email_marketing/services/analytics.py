"""Email analytics service.

Handles campaign analytics aggregation, click heatmap generation,
engagement tier computation, and device breakdown analysis.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from apps.email_marketing.models.analytics import EmailAnalytics
from apps.email_marketing.models.campaign import EmailCampaign
from apps.email_marketing.models.subscriber import EmailSubscriber


def aggregate_campaign_analytics(campaign_id: int) -> dict[str, Any]:
    """Aggregate analytics for a completed or sending campaign.

    Pulls stats from the campaign record and computes derived metrics.

    Args:
        campaign_id: Primary key of the email campaign.

    Returns:
        Dict with all aggregated analytics fields.
    """
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
    except EmailCampaign.DoesNotExist:
        return {"error": "Campaign not found"}
    analytics, _ = EmailAnalytics.objects.get_or_create(
        campaign=campaign,
        defaults={"tenant_id": campaign.tenant_id},
    )
    analytics.sent = campaign.total_recipients
    analytics.delivered = campaign.delivered
    analytics.opens = campaign.opens
    analytics.unique_opens = campaign.unique_opens
    analytics.clicks = campaign.clicks
    analytics.unique_clicks = campaign.unique_clicks
    analytics.bounces = campaign.bounces
    analytics.hard_bounces = campaign.hard_bounces
    analytics.spam_complaints = campaign.spam_complaints
    analytics.unsubscribes = campaign.unsubscribes
    analytics.revenue = campaign.revenue
    analytics.calculated_at = datetime.now(UTC)
    analytics.save()
    return {
        "campaign_id": str(campaign.id),
        "name": campaign.name,
        "open_rate": analytics.open_rate,
        "click_rate": analytics.click_rate,
        "ctr": analytics.ctr,
        "bounce_rate": analytics.bounce_rate,
        "conversion_rate": analytics.conversion_rate,
        "revenue_per_email": analytics.revenue_per_email,
        "delivered": analytics.delivered,
        "unique_opens": analytics.unique_opens,
        "unique_clicks": analytics.unique_clicks,
        "calculated_at": analytics.calculated_at.isoformat(),
    }


def generate_click_heatmap(
    blocks: list[dict[str, Any]],
    click_events: list[dict[str, Any]],
    total_delivered: int = 1,
) -> list[dict[str, Any]]:
    """Generate click heatmap data per template block.

    Maps click events to template blocks and computes
    click density per block.

    Args:
        blocks: Template block definitions.
        click_events: List of click event dicts with block_id, x, y.
        total_delivered: Total emails delivered (for rate calc).

    Returns:
        List of per-block heatmap entries sorted by clicks desc.
    """
    block_map: dict[str, dict[str, Any]] = {}
    for block in blocks:
        bid = block.get("id", "")
        if bid:
            block_map[bid] = {
                "block_id": bid,
                "block_type": block.get("type", "unknown"),
                "total_clicks": 0,
                "unique_clicks": 0,
                "click_rate": 0.0,
                "positions": [],
                "emails": set(),
            }
    for event in click_events:
        bid = event.get("block_id", "")
        if bid and bid in block_map:
            block_map[bid]["total_clicks"] += 1
            email_id = event.get("email_id")
            if email_id:
                block_map[bid]["emails"].add(str(email_id))
            pos = event.get("position")
            if pos:
                block_map[bid]["positions"].append(pos)
    results = []
    for bid, data in block_map.items():
        unique = len(data["emails"])
        rate = round(unique / total_delivered, 6) if total_delivered > 0 else 0.0
        results.append({
            "block_id": bid,
            "block_type": data["block_type"],
            "total_clicks": data["total_clicks"],
            "unique_clicks": unique,
            "click_rate": rate,
            "positions": data["positions"][:100],
        })
    results.sort(key=lambda x: x["total_clicks"], reverse=True)
    return results


def compute_engagement_tiers(
    tenant_id: str,
    total_subscribers: int | None = None,
) -> dict[str, Any]:
    """Compute engagement tier distribution for a tenant's subscribers.

    Groups subscribers by engagement score into tiers:
    Champions (top 10%), Loyal (top 25%), Potential (top 50%),
    At Risk (below 50%), Dormant (bottom 20%).

    Args:
        tenant_id: Tenant identifier.
        total_subscribers: Optional pre-counted total.

    Returns:
        Dict with tier counts and thresholds.
    """
    queryset = EmailSubscriber.objects.filter(
        tenant_id=tenant_id,
        status=EmailSubscriber.Status.ACTIVE,
    ).order_by("-engagement_score")
    if total_subscribers is None:
        total_subscribers = queryset.count()
    if total_subscribers == 0:
        return {
            "total": 0,
            "tiers": {
                "champions": 0,
                "loyal": 0,
                "potential": 0,
                "at_risk": 0,
                "dormant": 0,
            },
            "thresholds": {"champions": 0, "loyal": 0, "potential": 0, "at_risk": 0},
        }
    scores = list(queryset.values_list("engagement_score", flat=True))
    tiers = {}
    tier_defs = {
        "champions": int(total_subscribers * 0.1),
        "loyal": int(total_subscribers * 0.25),
        "potential": int(total_subscribers * 0.5),
        "at_risk": int(total_subscribers * 0.8),
        "dormant": total_subscribers,
    }
    thresholds = {}
    for tier_name, cutoff_idx in tier_defs.items():
        idx = min(cutoff_idx - 1, len(scores) - 1)
        idx = max(0, idx)
        thresholds[tier_name] = float(scores[idx])
    loyal_qs = queryset.filter(engagement_score__gte=thresholds["loyal"])
    champions_qs = loyal_qs.filter(engagement_score__gte=thresholds["champions"])
    loyal_only = loyal_qs.exclude(engagement_score__gte=thresholds["champions"])
    potential_qs = queryset.filter(
        engagement_score__gte=thresholds["potential"],
        engagement_score__lt=thresholds["loyal"],
    )
    at_risk_qs = queryset.filter(
        engagement_score__gte=thresholds["at_risk"],
        engagement_score__lt=thresholds["potential"],
    )
    dormant_qs = queryset.filter(engagement_score__lt=thresholds["at_risk"])
    tiers = {
        "champions": champions_qs.count(),
        "loyal": loyal_only.count(),
        "potential": potential_qs.count(),
        "at_risk": at_risk_qs.count(),
        "dormant": dormant_qs.count(),
    }
    return {
        "total": total_subscribers,
        "tiers": tiers,
        "thresholds": {k: round(v, 2) for k, v in thresholds.items()},
    }


def compute_device_breakdown(
    tenant_id: str,
    device_data: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute device and platform breakdown for email opens.

    Args:
        tenant_id: Tenant identifier.
        device_data: Optional pre-aggregated device event data.

    Returns:
        Dict with device, OS, and client breakdowns.
    """
    if device_data is None:
        return {
            "devices": {"desktop": 0, "mobile": 0, "tablet": 0, "unknown": 0},
            "oses": {},
            "clients": {},
            "total_tracked": 0,
        }
    devices: dict[str, int] = {"desktop": 0, "mobile": 0, "tablet": 0, "unknown": 0}
    oses: dict[str, int] = {}
    clients: dict[str, int] = {}
    for event in device_data:
        device = event.get("device", "unknown").lower()
        os_name = event.get("os", "Unknown")
        client = event.get("client", "Unknown")
        if device in devices:
            devices[device] += 1
        else:
            devices["unknown"] += 1
        oses[os_name] = oses.get(os_name, 0) + 1
        clients[client] = clients.get(client, 0) + 1
    total = sum(devices.values())
    return {
        "devices": devices,
        "oses": oses,
        "clients": clients,
        "total_tracked": total,
    }


def get_campaign_hourly_breakdown(
    campaign_id: int,
    events: list[dict[str, Any]],
) -> dict[str, list[int]]:
    """Aggregate opens and clicks by hour of day.

    Args:
        campaign_id: The campaign ID.
        events: List of event dicts with timestamp and event_type.

    Returns:
        Dict with hourly arrays for opens and clicks.
    """
    hourly_opens = [0] * 24
    hourly_clicks = [0] * 24
    for event in events:
        ts = event.get("timestamp")
        if not ts:
            continue
        try:
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                dt = ts
            hour = dt.hour
            if event.get("event_type") == "open":
                hourly_opens[hour] += 1
            elif event.get("event_type") == "click":
                hourly_clicks[hour] += 1
        except (ValueError, TypeError, AttributeError):
            continue
    return {
        "opens_by_hour": hourly_opens,
        "clicks_by_hour": hourly_clicks,
    }
