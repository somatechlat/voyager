"""Rank tracking service.

Implements position monitoring, SERP feature detection,
ranking change alerts, and historical trend analysis.
"""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.seo.models.keyword import Keyword
from apps.seo.models.rank import RankHistory, SERPTracking

logger = logging.getLogger(__name__)

# SERP feature types
_SERP_FEATURES = [
    "featured_snippet",
    "people_also_ask",
    "local_pack",
    "knowledge_panel",
    "top_stories",
    "image_pack",
    "video_carousel",
    "shopping_results",
    "site_links",
    "rich_results",
    "twitter_pack",
    "app_pack",
    "jobs",
    "events",
    "flights",
    "hotels",
    "recipes",
    "reviews",
]


def detect_serp_features(
    serp_data: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Detect SERP features from raw SERP data.

    Args:
        serp_data: Raw search result data.

    Returns:
        List of detected feature dicts with type and position.
    """
    if not serp_data:
        return []
    features: list[dict[str, Any]] = []
    for feature in _SERP_FEATURES:
        if serp_data.get(feature) or feature in str(serp_data):
            features.append(
                {
                    "type": feature,
                    "position": serp_data.get(f"{feature}_position"),
                    "present": True,
                }
            )
    return features


def calculate_position_change(current: int | None, previous: int | None) -> int:
    """Calculate position change.

    Positive = improved (moved up), negative = dropped.

    Args:
        current: Current position.
        previous: Previous position.

    Returns:
        Position change value.
    """
    if current is None or previous is None:
        return 0
    return previous - current


def should_alert(position_change: int, threshold: str) -> tuple[bool, str]:
    """Determine if ranking change warrants an alert.

    Args:
        position_change: The position change value.
        threshold: Alert threshold setting.

    Returns:
        Tuple of (should_alert, alert_type).
    """
    abs_change = abs(position_change)
    thresholds: dict[str, int] = {
        SERPTracking.AlertThreshold.SMALL: 3,
        SERPTracking.AlertThreshold.MEDIUM: 5,
        SERPTracking.AlertThreshold.LARGE: 10,
    }
    min_change = thresholds.get(threshold, 5)

    if abs_change < min_change or threshold == SERPTracking.AlertThreshold.NONE:
        return False, ""

    alert_type = "ranking_improved" if position_change > 0 else "ranking_dropped"
    return True, alert_type


def collect_ranking(
    tracking: SERPTracking,
    position: int | None,
    url: str = "",
    serp_features: list[dict[str, Any]] | None = None,
    competitors: list[dict[str, Any]] | None = None,
    page_title: str = "",
    page_description: str = "",
    location: str = "US",
    device: str = "desktop",
) -> dict[str, Any]:
    """Collect a single ranking snapshot and update tracking.

    Args:
        tracking: SERPTracking instance.
        position: Current SERP position.
        url: Ranking URL.
        serp_features: Detected SERP features.
        competitors: Top competitor data.
        page_title: Page title from SERP.
        page_description: Page description from SERP.
        location: Search location.
        device: Device type.

    Returns:
        Dict with ranking data and alert info.
    """
    serp_features = serp_features or []
    competitors = competitors or []

    previous = tracking.current_position
    change = calculate_position_change(position, previous)

    # Create history record
    history = RankHistory.objects.create(
        tracking=tracking,
        keyword_text=tracking.keyword.keyword,
        position=position,
        previous_position=previous,
        position_change=change,
        url=url,
        serp_features_json=[f.get("type") for f in serp_features],
        location=location,
        device=device,
        competitors_json=competitors,
        page_title=page_title,
        page_description=page_description,
    )

    # Update tracking snapshot
    tracking.previous_position = previous
    tracking.current_position = position
    tracking.position_change = change
    tracking.current_url = url
    tracking.serp_features_json = [f.get("type") for f in serp_features]
    tracking.last_checked_at = timezone.now()
    tracking.check_count += 1

    if position:
        if tracking.best_position is None or position < tracking.best_position:
            tracking.best_position = position
        if tracking.worst_position is None or position > tracking.worst_position:
            tracking.worst_position = position

    tracking.save()

    # Update keyword position
    keyword = tracking.keyword
    keyword.current_position = position
    keyword.previous_position = previous
    keyword.position_change = change
    keyword.tracked_at = timezone.now()
    keyword.save(
        update_fields=["current_position", "previous_position", "position_change", "tracked_at"]
    )

    # Check alerts
    needs_alert, alert_type = should_alert(change, tracking.alert_threshold)

    result: dict[str, Any] = {
        "history_id": str(history.id),
        "keyword": tracking.keyword.keyword,
        "position": position,
        "previous_position": previous,
        "change": change,
        "url": url,
        "location": location,
        "device": device,
        "alert": None,
    }

    if needs_alert:
        result["alert"] = {
            "type": alert_type,
            "keyword": tracking.keyword.keyword,
            "position": position,
            "change": change,
            "location": location,
            "device": device,
        }

    return result


def get_ranking_trend(tracking: SERPTracking, days: int = 30) -> list[dict[str, Any]]:
    """Get ranking trend for a tracked keyword.

    Args:
        tracking: SERPTracking instance.
        days: Number of days to look back.

    Returns:
        List of history entries with position and date.
    """
    from datetime import timedelta

    since = timezone.now() - timedelta(days=days)
    history = (
        RankHistory.objects.filter(
            tracking=tracking,
            tracked_at__gte=since,
        )
        .order_by("tracked_at")
        .values("position", "tracked_at", "url", "serp_features_json")
    )
    return [
        {
            "position": h["position"],
            "tracked_at": h["tracked_at"].isoformat() if h["tracked_at"] else None,
            "url": h["url"],
            "serp_features": h["serp_features_json"],
        }
        for h in history
    ]


def get_ranking_distribution(tenant_id: str) -> dict[str, int]:
    """Get keyword ranking distribution for a tenant.

    Args:
        tenant_id: Tenant scope identifier.

    Returns:
        Dict with top3, top10, top50, top100, not_ranked counts.
    """
    tracked = SERPTracking.objects.filter(tenant_id=tenant_id, is_active=True)
    keywords = Keyword.objects.filter(tenant_id=tenant_id, is_tracked=True)

    top3 = sum(1 for k in keywords if k.current_position and k.current_position <= 3)
    top10 = sum(1 for k in keywords if k.current_position and k.current_position <= 10)
    top50 = sum(1 for k in keywords if k.current_position and k.current_position <= 50)
    top100 = sum(1 for k in keywords if k.current_position and k.current_position <= 100)
    not_ranked = tracked.count() - top100

    return {
        "top3": top3,
        "top10": top10,
        "top50": top50,
        "top100": top100,
        "not_ranked": max(0, not_ranked),
        "total_tracked": tracked.count(),
    }
