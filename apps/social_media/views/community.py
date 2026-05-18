"""Community management views.

Endpoints for community member listing, VIP identification,
engagement scoring, and community health metrics.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.social_media.models import CommunityMember
from apps.social_media.services.community import (
    calculate_engagement_score,
    get_community_health,
    identify_vips,
    update_member_scores,
)

router = Router(auth=VoyagerKeycloakBearer())


class MemberOut:
    """Output schema for a community member."""

    id: str
    platform: str
    name: str
    avatar: str
    bio: str
    followers: int
    following: int
    engagement_score: float
    influence_score: float
    loyalty_score: float
    vip_score: float
    tier: str
    first_seen_at: str
    last_active_at: str
    total_interactions: int


class MemberScoreOut:
    """Output schema for member engagement score."""

    score: float
    tier: str
    breakdown: dict[str, int]
    days: int


@router.get("/members", response=list[MemberOut], tags=["SM Community"])
def list_members(
    request,
    tenant_id: str = "",
    platform: str = "",
    tier: str = "",
    limit: int = 50,
    offset: int = 0,
):
    """List community members with filters."""
    qs = CommunityMember.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if platform:
        qs = qs.filter(platform=platform)
    if tier:
        qs = qs.filter(tier=tier)
    qs = qs.order_by("-vip_score")[offset : offset + limit]
    return [_member_to_dict(m) for m in qs]


@router.get("/members/{member_id}", response=MemberOut, tags=["SM Community"])
def get_member(request, member_id: str):
    """Get a single community member."""
    member = get_object_or_404(CommunityMember, id=member_id)
    return _member_to_dict(member)


@router.get("/members/{member_id}/score", response=MemberScoreOut, tags=["SM Community"])
def get_member_score(request, member_id: str, days: int = 90):
    """Calculate engagement score for a member."""
    member = get_object_or_404(CommunityMember, id=member_id)
    result = calculate_engagement_score(member, days=days)
    return MemberScoreOut(**result)


@router.post("/members/{member_id}/rescore", response=MemberOut, tags=["SM Community"])
def rescore_member(request, member_id: str):
    """Recalculate all scores for a member."""
    member = get_object_or_404(CommunityMember, id=member_id)
    update_member_scores(member)
    return _member_to_dict(member)


@router.get("/vips", response=dict, tags=["SM Community"])
def get_vips(request, tenant_id: str = "", platform: str = ""):
    """Identify VIP community members."""
    result = identify_vips(
        tenant_id=tenant_id,
        platform=platform or None,
    )
    return result


@router.get("/health", response=dict, tags=["SM Community"])
def community_health(request, tenant_id: str = "", days: int = 30):
    """Get community health metrics."""
    return get_community_health(tenant_id=tenant_id, days=days)


@router.get("/members/stats/tiers", response=dict, tags=["SM Community"])
def tier_stats(request, tenant_id: str = ""):
    """Get member count per tier."""
    qs = CommunityMember.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return {
        "champion": qs.filter(tier="champion").count(),
        "advocate": qs.filter(tier="advocate").count(),
        "engaged": qs.filter(tier="engaged").count(),
        "passive": qs.filter(tier="passive").count(),
    }


def _member_to_dict(m: CommunityMember) -> dict[str, Any]:
    """Convert CommunityMember to response dict."""
    return {
        "id": str(m.id),
        "platform": m.platform,
        "name": m.name,
        "avatar": m.avatar,
        "bio": m.bio,
        "followers": m.followers,
        "following": m.following,
        "engagement_score": float(m.engagement_score),
        "influence_score": float(m.influence_score),
        "loyalty_score": float(m.loyalty_score),
        "vip_score": float(m.vip_score),
        "tier": m.tier,
        "first_seen_at": m.first_seen_at.isoformat(),
        "last_active_at": m.last_active_at.isoformat(),
        "total_interactions": m.total_interactions,
    }
