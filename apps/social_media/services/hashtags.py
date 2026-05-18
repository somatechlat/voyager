"""Hashtag research service.

Handles hashtag competition scoring, trend analysis, opportunity
calculation, and platform-specific recommendations.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from apps.social_media.models import HashtagResearch

logger = logging.getLogger(__name__)

VOLUME_LOG_MIN = 3.0
VOLUME_LOG_MAX = 9.0
RECENT_MIN = 100
RECENT_MAX = 100000
ENGAGEMENT_MIN = 10.0
ENGAGEMENT_MAX = 10000.0


def score_hashtag_competition(
    hashtag: str,
    platform: str,
    tenant_id: str,
) -> dict[str, Any] | None:
    """Score a hashtag's competitiveness and opportunity.

    :param hashtag: Hashtag string (without #).
    :param platform: Platform name.
    :param tenant_id: Tenant scope.
    :returns: Score dict or None if not found.
    """
    try:
        entry = HashtagResearch.objects.get(
            tenant_id=tenant_id, hashtag__iexact=hashtag, platform=platform
        )
    except HashtagResearch.DoesNotExist:
        return None

    factors = {
        "volume": entry.total_posts or 0,
        "recent_volume": entry.posts_last_week or 0,
        "avg_engagement": float(entry.avg_engagement) if entry.avg_engagement else 0,
        "top_post_threshold": (
            float(entry.top_post_min_engagement) if entry.top_post_min_engagement else 0
        ),
    }

    volume_score = _minmax_normalize(
        math.log10(max(factors["volume"], 1)), VOLUME_LOG_MIN, VOLUME_LOG_MAX
    )
    recent_score = _minmax_normalize(factors["recent_volume"], RECENT_MIN, RECENT_MAX)
    engagement_score = _minmax_normalize(
        factors["top_post_threshold"], ENGAGEMENT_MIN, ENGAGEMENT_MAX
    )

    competition = (volume_score * 0.4 + recent_score * 0.35 + engagement_score * 0.25) * 100

    opportunity = (
        (1 - competition / 100)
        * _minmax_normalize(math.log10(max(factors["volume"], 1)), VOLUME_LOG_MIN, VOLUME_LOG_MAX)
        * 100
    )

    recommendation = _opportunity_to_recommendation(opportunity)

    entry.competition_score = round(competition, 2)
    entry.opportunity_score = round(opportunity, 2)
    entry.recommendation = recommendation
    entry.save(update_fields=["competition_score", "opportunity_score", "recommendation"])

    return {
        "hashtag": hashtag,
        "platform": platform,
        "competition": round(competition, 2),
        "opportunity": round(opportunity, 2),
        "recommendation": recommendation,
        "metrics": factors,
    }


def get_trending_hashtags(
    tenant_id: str,
    platform: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get currently trending hashtags for a tenant.

    :param tenant_id: Tenant scope.
    :param platform: Optional platform filter.
    :param limit: Max results.
    :returns: List of trending hashtag dicts.
    """
    qs = HashtagResearch.objects.filter(tenant_id=tenant_id)
    if platform:
        qs = qs.filter(platform=platform)
    qs = qs.filter(trend_direction__in=["rising", "viral"]).order_by(
        "-trend_percentage", "-opportunity_score"
    )[:limit]

    return [
        {
            "hashtag": h.hashtag,
            "platform": h.platform,
            "total_posts": h.total_posts,
            "posts_last_week": h.posts_last_week,
            "trend_direction": h.trend_direction,
            "trend_percentage": float(h.trend_percentage) if h.trend_percentage else 0,
            "opportunity_score": float(h.opportunity_score) if h.opportunity_score else 0,
            "recommendation": h.recommendation,
        }
        for h in qs
    ]


def suggest_hashtags(
    tenant_id: str,
    topic: str,
    platform: str = "instagram",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Suggest hashtags for a given topic.

    :param tenant_id: Tenant scope.
    :param topic: Topic or seed hashtag.
    :param platform: Target platform.
    :param limit: Max results.
    :returns: List of suggested hashtag dicts.
    """
    qs = (
        HashtagResearch.objects.filter(
            tenant_id=tenant_id,
            platform=platform,
        )
        .filter(
            models.Q(hashtag__icontains=topic)
            | models.Q(category__icontains=topic)
            | models.Q(related_hashtags__contains=[topic])
        )
        .order_by("-opportunity_score")[:limit]
    )

    return [
        {
            "hashtag": h.hashtag,
            "opportunity_score": float(h.opportunity_score) if h.opportunity_score else 0,
            "competition_score": float(h.competition_score) if h.competition_score else 0,
            "recommendation": h.recommendation,
            "total_posts": h.total_posts,
            "posts_last_week": h.posts_last_week,
            "trend_direction": h.trend_direction,
        }
        for h in qs
    ]


def update_trend_direction(
    entry: HashtagResearch,
) -> None:
    """Update the trend direction based on recent posting activity.

    :param entry: HashtagResearch instance.
    """
    total = entry.total_posts or 1
    recent = entry.posts_last_week or 0

    if total == 0:
        entry.trend_direction = "stable"
        return

    ratio = recent / total
    if ratio > 0.1:
        entry.trend_direction = "viral"
    elif ratio > 0.05:
        entry.trend_direction = "rising"
    elif ratio < 0.01:
        entry.trend_direction = "falling"
    else:
        entry.trend_direction = "stable"

    entry.trend_percentage = round(ratio * 100, 2)


def _minmax_normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to 0-1 range.

    :param value: Raw value.
    :param min_val: Minimum of range.
    :param max_val: Maximum of range.
    :returns: Normalized value clamped to 0-1.
    """
    if max_val == min_val:
        return 0.5
    normalized = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))


def _opportunity_to_recommendation(score: float) -> str:
    """Map opportunity score to recommendation.

    :param score: Opportunity score (0-100).
    :returns: Recommendation string.
    """
    if score >= 70:
        return "highly_recommended"
    if score >= 50:
        return "recommended"
    if score >= 30:
        return "consider"
    return "avoid"


# Import at end to avoid circular import
from django.db import models  # noqa: E402
