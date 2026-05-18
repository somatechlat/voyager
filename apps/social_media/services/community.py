"""Community management service.

Handles engagement scoring, VIP identification, community health
analysis, and interaction tracking across platforms.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.db.models import Count, Sum
from django.utils import timezone

from apps.social_media.models import CommunityMember, InboxMessage, SocialComment

logger = logging.getLogger(__name__)

INTERACTION_WEIGHTS = {
    "comment": 3,
    "share": 5,
    "like": 1,
    "mention": 4,
    "dm": 6,
    "review": 8,
    "ugc": 10,
}

TIER_THRESHOLDS = {
    "champion": 90,
    "advocate": 70,
    "engaged": 40,
    "passive": 0,
}


def calculate_engagement_score(
    member: CommunityMember,
    days: int = 90,
) -> dict[str, Any]:
    """Calculate a weighted engagement score for a community member.

    :param member: CommunityMember instance.
    :param days: Number of days to look back.
    :returns: Dict with score, percentile, tier, breakdown.
    """
    since = timezone.now() - timedelta(days=days)

    comment_count = SocialComment.objects.filter(
        tenant_id=member.tenant_id,
        author_platform_id=member.platform_user_id,
        received_at__gte=since,
    ).count()

    message_count = InboxMessage.objects.filter(
        tenant_id=member.tenant_id,
        author_platform_id=member.platform_user_id,
        received_at__gte=since,
    ).count()

    breakdown: dict[str, int] = {
        "comment": comment_count,
        "dm": message_count,
        "like": 0,
        "share": 0,
        "mention": 0,
        "review": 0,
        "ugc": 0,
    }

    weighted_score = sum(INTERACTION_WEIGHTS.get(k, 1) * v for k, v in breakdown.items())

    active_types = sum(1 for v in breakdown.values() if v > 0)
    recency_multiplier = 1.0 + (active_types / max(len(breakdown), 1))
    consistency_bonus = min(active_types / 3.0, 1.0)

    final_score = weighted_score * recency_multiplier * (1 + consistency_bonus)
    final_score = min(final_score, 999999.99)

    tier = _score_to_tier(final_score)

    return {
        "score": round(final_score, 2),
        "tier": tier,
        "breakdown": breakdown,
        "days": days,
    }


def identify_vips(
    tenant_id: str,
    platform: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Identify VIP community members by composite scoring.

    :param tenant_id: Tenant scope.
    :param platform: Optional platform filter.
    :returns: Dict with champions, advocates, engaged tiers.
    """
    qs = CommunityMember.objects.filter(tenant_id=tenant_id)
    if platform:
        qs = qs.filter(platform=platform)

    members = list(qs.order_by("-vip_score"))
    if not members:
        return {"champions": [], "advocates": [], "engaged": []}

    total = len(members)
    champion_cutoff = max(1, int(total * 0.01))
    advocate_cutoff = max(1, int(total * 0.05))
    engaged_cutoff = max(1, int(total * 0.10))

    def member_to_dict(m: CommunityMember) -> dict[str, Any]:
        return {
            "id": str(m.id),
            "name": m.name,
            "platform": m.platform,
            "avatar": m.avatar,
            "vip_score": float(m.vip_score),
            "engagement_score": float(m.engagement_score),
            "influence_score": float(m.influence_score),
            "loyalty_score": float(m.loyalty_score),
            "tier": m.tier,
            "followers": m.followers,
        }

    return {
        "champions": [member_to_dict(m) for m in members[:champion_cutoff]],
        "advocates": [member_to_dict(m) for m in members[champion_cutoff:advocate_cutoff]],
        "engaged": [member_to_dict(m) for m in members[advocate_cutoff:engaged_cutoff]],
    }


def update_member_scores(member: CommunityMember) -> None:
    """Recalculate all scores for a community member in place.

    :param member: CommunityMember instance.
    """
    engagement = calculate_engagement_score(member, days=90)
    member.engagement_score = engagement["score"]

    influence = _calculate_influence(member)
    member.influence_score = influence

    loyalty = _calculate_loyalty(member)
    member.loyalty_score = loyalty

    vip = float(member.engagement_score) * 0.4 + float(influence) * 0.35 + float(loyalty) * 0.25
    member.vip_score = round(min(vip, 999999.99), 2)
    member.tier = engagement["tier"]
    member.save(
        update_fields=[
            "engagement_score",
            "influence_score",
            "loyalty_score",
            "vip_score",
            "tier",
            "updated_at",
        ]
    )


def get_community_health(
    tenant_id: str,
    days: int = 30,
) -> dict[str, Any]:
    """Get community health metrics.

    :param tenant_id: Tenant scope.
    :param days: Lookback period.
    :returns: Health metrics dict.
    """
    since = timezone.now() - timedelta(days=days)

    total_members = CommunityMember.objects.filter(tenant_id=tenant_id).count()
    active_members = (
        CommunityMember.objects.filter(tenant_id=tenant_id, last_active_at__gte=since)
        .values("platform")
        .annotate(count=Count("id"))
    )

    tier_counts = (
        CommunityMember.objects.filter(tenant_id=tenant_id)
        .values("tier")
        .annotate(count=Count("id"))
    )

    new_members = CommunityMember.objects.filter(
        tenant_id=tenant_id, first_seen_at__gte=since
    ).count()

    total_interactions = sum(
        CommunityMember.objects.filter(tenant_id=tenant_id)
        .aggregate(total=Sum("total_interactions"))
        .get("total")
        or 0,
    )

    avg_engagement = 0.0
    if total_members > 0:
        avg_engagement = (
            float(
                CommunityMember.objects.filter(tenant_id=tenant_id)
                .aggregate(avg=Sum("engagement_score"))
                .get("avg")
                or 0,
            )
            / total_members
        )

    return {
        "total_members": total_members,
        "active_by_platform": {a["platform"]: a["count"] for a in active_members},
        "tier_distribution": {t["tier"]: t["count"] for t in tier_counts},
        "new_members_period": new_members,
        "total_interactions": total_interactions,
        "avg_engagement_score": round(avg_engagement, 2),
        "period_days": days,
    }


def _calculate_influence(member: CommunityMember) -> float:
    """Calculate influence score based on followers and reach.

    :param member: CommunityMember instance.
    :returns: Influence score.
    """
    followers = member.followers or 0
    score = min(followers / 1000.0, 100.0)
    return round(score, 2)


def _calculate_loyalty(member: CommunityMember) -> float:
    """Calculate loyalty score based on tenure and consistency.

    :param member: CommunityMember instance.
    :returns: Loyalty score.
    """
    tenure_days = (timezone.now() - member.first_seen_at).days
    score = min(tenure_days / 30.0 + (member.total_interactions or 0) * 0.5, 100.0)
    return round(score, 2)


def _score_to_tier(score: float) -> str:
    """Map a numeric score to a tier.

    :param score: Engagement score.
    :returns: Tier name.
    """
    if score >= TIER_THRESHOLDS["champion"]:
        return "champion"
    if score >= TIER_THRESHOLDS["advocate"]:
        return "advocate"
    if score >= TIER_THRESHOLDS["engaged"]:
        return "engaged"
    return "passive"
