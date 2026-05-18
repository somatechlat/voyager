"""Hashtag research views.

Endpoints for hashtag research, competition scoring, trending,
and suggestions.
"""

from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.social_media.models import HashtagResearch
from apps.social_media.services.hashtags import (
    get_trending_hashtags,
    score_hashtag_competition,
    suggest_hashtags,
)

router = Router(auth=VoyagerKeycloakBearer())


class HashtagOut:
    """Output schema for a hashtag research record."""

    id: str
    hashtag: str
    platform: str
    total_posts: int
    posts_last_week: int
    posts_last_day: int
    avg_engagement: float
    competition_score: float
    opportunity_score: float
    recommendation: str
    trend_direction: str
    trend_percentage: float
    related_hashtags: list[str]
    category: str
    researched_at: str


class HashtagScoreOut:
    """Output schema for hashtag competition score."""

    hashtag: str
    platform: str
    competition: float
    opportunity: float
    recommendation: str
    metrics: dict[str, Any]


class ResearchIn:
    """Input schema for creating a hashtag research record."""

    hashtag: str
    platform: str
    total_posts: int = 0
    posts_last_week: int = 0
    posts_last_day: int = 0
    avg_engagement: float = 0
    top_post_min_engagement: float = 0
    category: str = ""
    related_hashtags: list[str] = []


@router.get("/hashtags", response=list[HashtagOut], tags=["SM Hashtags"])
def list_hashtags(
    request,
    tenant_id: str = "",
    platform: str = "",
    recommendation: str = "",
    category: str = "",
    limit: int = 50,
    offset: int = 0,
):
    """List hashtag research records with filters."""
    qs = HashtagResearch.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if platform:
        qs = qs.filter(platform=platform)
    if recommendation:
        qs = qs.filter(recommendation=recommendation)
    if category:
        qs = qs.filter(category__icontains=category)
    qs = qs.order_by("-opportunity_score")[offset : offset + limit]
    return [_hashtag_to_dict(h) for h in qs]


@router.get("/hashtags/{hashtag_id}", response=HashtagOut, tags=["SM Hashtags"])
def get_hashtag(request, hashtag_id: str):
    """Get a single hashtag research record."""
    h = get_object_or_404(HashtagResearch, id=hashtag_id)
    return _hashtag_to_dict(h)


@router.post("/hashtags", response=HashtagOut, tags=["SM Hashtags"])
def create_hashtag_research(request, payload: ResearchIn):
    """Create a hashtag research record."""
    tenant_id = getattr(request, "tenant_id", "default")
    h = HashtagResearch.objects.create(
        tenant_id=tenant_id,
        hashtag=payload.hashtag.lstrip("#").lower(),
        platform=payload.platform,
        total_posts=payload.total_posts,
        posts_last_week=payload.posts_last_week,
        posts_last_day=payload.posts_last_day,
        avg_engagement=payload.avg_engagement or None,
        top_post_min_engagement=payload.top_post_min_engagement or None,
        category=payload.category,
        related_hashtags=payload.related_hashtags,
    )
    return _hashtag_to_dict(h)


@router.get("/hashtags/{hashtag_id}/score", response=HashtagScoreOut, tags=["SM Hashtags"])
def get_hashtag_score(request, hashtag_id: str):
    """Get competition and opportunity score for a hashtag."""
    h = get_object_or_404(HashtagResearch, id=hashtag_id)
    result = score_hashtag_competition(h.hashtag, h.platform, h.tenant_id)
    if result is None:
        return {"hashtag": h.hashtag, "platform": h.platform, "competition": 0, "opportunity": 0, "recommendation": "unknown", "metrics": {}}
    return HashtagScoreOut(**result)


@router.get("/trending", response=list, tags=["SM Hashtags"])
def trending(request, tenant_id: str = "", platform: str = "", limit: int = 20):
    """Get trending hashtags."""
    return get_trending_hashtags(
        tenant_id=tenant_id,
        platform=platform or None,
        limit=limit,
    )


@router.get("/suggest", response=list, tags=["SM Hashtags"])
def suggest(
    request,
    tenant_id: str = "",
    topic: str = "",
    platform: str = "instagram",
    limit: int = 10,
):
    """Suggest hashtags for a topic."""
    if not topic:
        return []
    return suggest_hashtags(
        tenant_id=tenant_id,
        topic=topic,
        platform=platform,
        limit=limit,
    )


@router.get("/hashtags/stats/overview", response=dict, tags=["SM Hashtags"])
def hashtag_stats(request, tenant_id: str = ""):
    """Get hashtag statistics."""
    qs = HashtagResearch.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return {
        "total_researched": qs.count(),
        "by_recommendation": {
            "highly_recommended": qs.filter(recommendation="highly_recommended").count(),
            "recommended": qs.filter(recommendation="recommended").count(),
            "consider": qs.filter(recommendation="consider").count(),
            "avoid": qs.filter(recommendation="avoid").count(),
        },
        "by_trend": {
            "rising": qs.filter(trend_direction="rising").count(),
            "viral": qs.filter(trend_direction="viral").count(),
            "stable": qs.filter(trend_direction="stable").count(),
            "falling": qs.filter(trend_direction="falling").count(),
        },
    }


def _hashtag_to_dict(h: HashtagResearch) -> dict[str, Any]:
    """Convert HashtagResearch to response dict."""
    return {
        "id": str(h.id),
        "hashtag": h.hashtag,
        "platform": h.platform,
        "total_posts": h.total_posts,
        "posts_last_week": h.posts_last_week,
        "posts_last_day": h.posts_last_day,
        "avg_engagement": float(h.avg_engagement) if h.avg_engagement else 0,
        "competition_score": float(h.competition_score) if h.competition_score else 0,
        "opportunity_score": float(h.opportunity_score) if h.opportunity_score else 0,
        "recommendation": h.recommendation,
        "trend_direction": h.trend_direction,
        "trend_percentage": float(h.trend_percentage) if h.trend_percentage else 0,
        "related_hashtags": h.related_hashtags,
        "category": h.category,
        "researched_at": h.researched_at.isoformat(),
    }
