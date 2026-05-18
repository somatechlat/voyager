"""Influencer discovery and vetting service.

Handles influencer search, authenticity verification, audience
analysis, and outreach tracking.
"""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.social_media.models import InfluencerProfile

logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {"high": 25, "medium": 15, "low": 5}


def search_influencers(
    tenant_id: str,
    niche: list[str] | None = None,
    location: str | None = None,
    min_followers: int | None = None,
    max_followers: int | None = None,
    min_engagement: float | None = None,
    platforms: list[str] | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search the influencer database by criteria.

    :param tenant_id: Tenant scope.
    :param niche: List of niche tags.
    :param location: Geographic location.
    :param min_followers: Minimum follower count.
    :param max_followers: Maximum follower count.
    :param min_engagement: Minimum engagement rate.
    :param platforms: List of platform names.
    :param limit: Max results.
    :returns: List of ranked influencer dicts.
    """
    qs = InfluencerProfile.objects.filter(tenant_id=tenant_id)

    if platforms:
        qs = qs.filter(platform__in=platforms)
    if niche:
        qs = qs.filter(niche__overlap=niche)
    if location:
        qs = qs.filter(location__icontains=location)
    if min_followers is not None:
        qs = qs.filter(followers__gte=min_followers)
    if max_followers is not None:
        qs = qs.filter(followers__lte=max_followers)
    if min_engagement is not None:
        qs = qs.filter(engagement_rate__gte=min_engagement)

    results: list[dict[str, Any]] = []
    for inf in qs.order_by("-match_score")[:limit]:
        match_score = float(inf.match_score) if inf.match_score else 0
        engagement = float(inf.engagement_rate) if inf.engagement_rate else 0
        authenticity = float(inf.authenticity_score) if inf.authenticity_score else 0
        content_quality = float(inf.content_quality_score) if inf.content_quality_score else 0

        results.append(
            {
                "id": str(inf.id),
                "name": inf.name,
                "platform": inf.platform,
                "avatar": inf.avatar,
                "followers": inf.followers,
                "engagement_rate": engagement,
                "niche": inf.niche,
                "location": inf.location,
                "authenticity_score": authenticity,
                "rate_estimate": float(inf.rate_estimate) if inf.rate_estimate else 0,
                "content_quality_score": content_quality,
                "match_score": match_score,
                "status": inf.status,
                "outreach_status": inf.outreach_status,
            }
        )

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results


def verify_authenticity(influencer: InfluencerProfile) -> dict[str, Any]:
    """Verify influencer authenticity and detect red flags.

    :param influencer: InfluencerProfile instance.
    :returns: Dict with score, red_flags, verified status.
    """
    red_flags: list[dict[str, Any]] = []

    followers = influencer.followers or 0
    following = influencer.following or 0

    if followers > 0 and following / followers > 0.8:
        red_flags.append(
            {
                "type": "high_followback",
                "severity": "medium",
                "detail": f"following/followers ratio: {following/followers:.2f}",
            }
        )

    engagement = float(influencer.engagement_rate) if influencer.engagement_rate else 0
    if followers > 10000 and engagement < 0.005:
        red_flags.append(
            {
                "type": "low_engagement",
                "severity": "high",
                "detail": f"Engagement rate {engagement:.4f} is very low for {followers} followers",
            }
        )

    if followers > 0 and followers < 500 and engagement > 0.5:
        red_flags.append(
            {
                "type": "suspicious_engagement",
                "severity": "medium",
                "detail": "Engagement rate unrealistically high for follower count",
            }
        )

    penalty = sum(SEVERITY_WEIGHTS.get(f["severity"], 5) for f in red_flags)
    score = max(0, 100 - penalty)

    influencer.authenticity_score = score
    influencer.red_flags = red_flags
    influencer.save(update_fields=["authenticity_score", "red_flags"])

    return {
        "score": score,
        "red_flags": red_flags,
        "verified": score >= 70,
    }


def estimate_rate(influencer: InfluencerProfile) -> dict[str, Any]:
    """Estimate collaboration cost for an influencer.

    :param influencer: InfluencerProfile instance.
    :returns: Dict with estimated rate and breakdown.
    """
    followers = influencer.followers or 0
    engagement = float(influencer.engagement_rate) if influencer.engagement_rate else 0
    authenticity = float(influencer.authenticity_score) if influencer.authenticity_score else 100

    base_rate = followers * 0.01
    engagement_multiplier = 1.0 + (engagement * 100)
    authenticity_multiplier = authenticity / 100.0

    estimated = base_rate * engagement_multiplier * authenticity_multiplier
    estimated = max(50, min(estimated, 100000))

    influencer.rate_estimate = round(estimated, 2)
    influencer.save(update_fields=["rate_estimate"])

    return {
        "estimated_rate_usd": round(estimated, 2),
        "base_rate": round(base_rate, 2),
        "engagement_multiplier": round(engagement_multiplier, 2),
        "authenticity_multiplier": round(authenticity_multiplier, 2),
    }


def calculate_match_score(
    influencer: InfluencerProfile,
    criteria: dict[str, Any],
) -> float:
    """Calculate a composite match score for an influencer against criteria.

    :param influencer: InfluencerProfile instance.
    :param criteria: Search criteria dict.
    :returns: Match score 0-100.
    """
    score = 0.0
    niche = criteria.get("niche", [])
    if niche and influencer.niche:
        overlap = len(set(niche) & set(influencer.niche))
        score += (overlap / max(len(niche), 1)) * 30
    else:
        score += 15

    engagement = float(influencer.engagement_rate) if influencer.engagement_rate else 0
    score += min(engagement * 2500, 25)

    authenticity = float(influencer.authenticity_score) if influencer.authenticity_score else 0
    score += (authenticity / 100.0) * 20

    content_quality = (
        float(influencer.content_quality_score) if influencer.content_quality_score else 0
    )
    score += (content_quality / 100.0) * 15

    location = criteria.get("location")
    if location and influencer.location:
        if location.lower() in influencer.location.lower():
            score += 10
    else:
        score += 5

    score = min(score, 100.0)
    influencer.match_score = round(score, 2)
    influencer.save(update_fields=["match_score"])
    return score


def update_outreach_status(
    influencer: InfluencerProfile,
    status: str,
) -> None:
    """Update the outreach status and timestamps.

    :param influencer: InfluencerProfile instance.
    :param status: New outreach status.
    """
    influencer.outreach_status = status
    now = timezone.now()
    if status == "email_sent" or status == "dm_sent":
        influencer.outreach_sent_at = now
    elif status in ("responded", "interested", "not_interested"):
        influencer.responded_at = now
    influencer.save(update_fields=["outreach_status", "outreach_sent_at", "responded_at"])
