"""Social listening views.

Endpoints for mention collection, sentiment analysis, alerts,
and filtering.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.social_media.models import SocialMention
from apps.social_media.services.listening import (
    analyze_sentiment,
    check_alerts,
    collect_mention,
    filter_mentions,
    get_mention_summary,
)

router = Router(auth=VoyagerKeycloakBearer())


class MentionOut:
    """Output schema for a social mention."""

    id: str
    platform: str
    mention_type: str
    tracked_term: str
    author_name: str
    author_avatar: str
    author_followers: int
    text: str
    url: str
    sentiment: str
    sentiment_score: float
    influence_score: float
    reach_estimate: int
    language: str
    is_alert_triggered: bool
    alert_reason: str
    mentioned_at: str


class CollectMentionIn:
    """Input schema for collecting a mention."""

    platform: str
    id: str = ""
    mention_type: str = "brand"
    tracked_term: str = ""
    author_name: str = ""
    author_id: str = ""
    author_avatar: str = ""
    author_followers: int = 0
    text: str = ""
    url: str = ""
    influence_score: float = 0
    reach_estimate: int = 0
    language: str = ""
    media_urls: list[str] = []
    created_at: str = ""


class SentimentIn:
    """Input schema for sentiment analysis."""

    text: str


class FilterMentionsIn:
    """Input schema for filtering mentions."""

    platform: str = ""
    sentiment: str = ""
    tracked_term: str = ""
    mention_type: str = ""
    alerts_only: bool = False
    since: str = ""


@router.get("/mentions", response=list[MentionOut], tags=["SM Listening"])
def list_mentions(
    request,
    tenant_id: str = "",
    platform: str = "",
    tracked_term: str = "",
    sentiment: str = "",
    limit: int = 50,
    offset: int = 0,
):
    """List social mentions with filters."""
    qs = SocialMention.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if platform:
        qs = qs.filter(platform=platform)
    if tracked_term:
        qs = qs.filter(tracked_term__iexact=tracked_term)
    if sentiment:
        qs = qs.filter(sentiment=sentiment)
    qs = qs.order_by("-mentioned_at")[offset : offset + limit]
    return [_mention_to_dict(m) for m in qs]


@router.get("/mentions/{mention_id}", response=MentionOut, tags=["SM Listening"])
def get_mention(request, mention_id: str):
    """Get a single mention."""
    m = get_object_or_404(SocialMention, id=mention_id)
    return _mention_to_dict(m)


@router.post("/mentions", response=dict, tags=["SM Listening"])
def create_mention(request, payload: CollectMentionIn):
    """Collect and process a social mention."""
    tenant_id = getattr(request, "tenant_id", "default")
    result = collect_mention(
        tenant_id=tenant_id,
        platform=payload.platform,
        mention_data=payload.dict(),
    )
    return result


@router.post("/sentiment", response=dict, tags=["SM Listening"])
def sentiment(request, payload: SentimentIn):
    """Analyze sentiment of text."""
    return analyze_sentiment(payload.text)


@router.get("/summary", response=dict, tags=["SM Listening"])
def summary(request, tenant_id: str = "", days: int = 7, tracked_term: str = ""):
    """Get mention summary statistics."""
    return get_mention_summary(
        tenant_id=tenant_id,
        days=days,
        tracked_term=tracked_term or None,
    )


@router.post("/mentions/filter", response=list[MentionOut], tags=["SM Listening"])
def filter_mentions_view(request, payload: FilterMentionsIn, limit: int = 100):
    """Filter mentions by multiple criteria."""
    tenant_id = getattr(request, "tenant_id", "default")
    filters = payload.dict()
    filters.pop("limit", None)
    return filter_mentions(tenant_id=tenant_id, filters=filters, limit=limit)


@router.get("/mentions/{mention_id}/alert", response=dict, tags=["SM Listening"])
def check_alert(request, mention_id: str):
    """Check if a mention triggers an alert."""
    m = get_object_or_404(SocialMention, id=mention_id)
    return check_alerts(m)


@router.get("/mentions/stats/alerts", response=dict, tags=["SM Listening"])
def alert_stats(request, tenant_id: str = ""):
    """Get alert statistics."""
    qs = SocialMention.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return {
        "total_mentions": qs.count(),
        "alerts_triggered": qs.filter(is_alert_triggered=True).count(),
        "alerts_by_platform": {
            p: qs.filter(platform=p, is_alert_triggered=True).count()
            for p in qs.values_list("platform", flat=True).distinct()
        },
    }


def _mention_to_dict(m: SocialMention) -> dict[str, Any]:
    """Convert SocialMention to response dict."""
    return {
        "id": str(m.id),
        "platform": m.platform,
        "mention_type": m.mention_type,
        "tracked_term": m.tracked_term,
        "author_name": m.author_name,
        "author_avatar": m.author_avatar,
        "author_followers": m.author_followers,
        "text": m.text,
        "url": m.url,
        "sentiment": m.sentiment,
        "sentiment_score": float(m.sentiment_score) if m.sentiment_score else 0,
        "influence_score": float(m.influence_score) if m.influence_score else 0,
        "reach_estimate": m.reach_estimate,
        "language": m.language,
        "is_alert_triggered": m.is_alert_triggered,
        "alert_reason": m.alert_reason,
        "mentioned_at": m.mentioned_at.isoformat(),
    }
