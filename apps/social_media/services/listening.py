"""Social listening service.

Handles mention collection, sentiment analysis, alert triggering,
and real-time stream filtering for brand monitoring.
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.social_media.models import SocialMention

logger = logging.getLogger(__name__)

POSITIVE_WORDS = {
    "great", "amazing", "excellent", "love", "best", "awesome",
    "fantastic", "wonderful", "perfect", "happy", "recommend",
    "outstanding", "brilliant", "superb", "impressive", "quality",
}

NEGATIVE_WORDS = {
    "terrible", "awful", "worst", "hate", "bad", "poor",
    "disappointing", "horrible", "broken", "useless", "waste",
    "never", "refund", "scam", "fake", "problem", "issue",
    "slow", "expensive", "overpriced", "regret",
}

INTENSITY_MULTIPLIERS = {
    "very": 1.3, "extremely": 1.5, "absolutely": 1.4,
    "really": 1.2, "totally": 1.2, "completely": 1.3,
}


def analyze_sentiment(text: str) -> dict[str, Any]:
    """Analyze sentiment of a text.

    :param text: Input text.
    :returns: Dict with sentiment label and score (-1.0 to +1.0).
    """
    if not text:
        return {"sentiment": "neutral", "score": 0.0}

    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return {"sentiment": "neutral", "score": 0.0}

    pos_count = 0
    neg_count = 0
    multiplier = 1.0

    for i, word in enumerate(words):
        if word in INTENSITY_MULTIPLIERS and i + 1 < len(words):
            multiplier = INTENSITY_MULTIPLIERS[word]
        if word in POSITIVE_WORDS:
            pos_count += 1 * multiplier
        if word in NEGATIVE_WORDS:
            neg_count += 1 * multiplier

    total = pos_count + neg_count
    if total == 0:
        return {"sentiment": "neutral", "score": 0.0}

    score = (pos_count - neg_count) / max(total, len(words) * 0.1)
    score = max(-1.0, min(1.0, score))

    if score >= 0.1:
        label = "positive"
    elif score <= -0.1:
        label = "negative"
    else:
        label = "neutral"

    return {"sentiment": label, "score": round(score, 3)}


def check_alerts(mention: SocialMention) -> dict[str, Any]:
    """Check if a mention should trigger an alert.

    :param mention: SocialMention instance.
    :returns: Alert dict with triggered, reason.
    """
    triggered = False
    reasons: list[str] = []

    influence = float(mention.influence_score) if mention.influence_score else 0
    sentiment_score = float(mention.sentiment_score) if mention.sentiment_score else 0

    if influence > 80:
        triggered = True
        reasons.append(f"high_influence:{influence}")

    if sentiment_score < -0.7:
        triggered = True
        reasons.append(f"negative_sentiment:{sentiment_score}")

    if mention.author_followers and mention.author_followers > 100000:
        triggered = True
        reasons.append(f"high_reach:{mention.author_followers}")

    mention.is_alert_triggered = triggered
    mention.alert_reason = "; ".join(reasons)
    mention.save(update_fields=["is_alert_triggered", "alert_reason"])

    return {"triggered": triggered, "reasons": reasons}


def collect_mention(
    tenant_id: str,
    platform: str,
    mention_data: dict[str, Any],
) -> dict[str, Any]:
    """Collect and process a social mention.

    :param tenant_id: Tenant scope.
    :param platform: Source platform.
    :param mention_data: Raw mention payload.
    :returns: Processing result.
    """
    sentiment = analyze_sentiment(mention_data.get("text", ""))

    mention = SocialMention.objects.create(
        tenant_id=tenant_id,
        platform=platform,
        platform_mention_id=str(mention_data.get("id", "")),
        mention_type=mention_data.get("mention_type", "brand"),
        tracked_term=mention_data.get("tracked_term", ""),
        author_name=mention_data.get("author_name", ""),
        author_platform_id=str(mention_data.get("author_id", "")),
        author_avatar=mention_data.get("author_avatar", ""),
        author_followers=mention_data.get("author_followers", 0),
        text=mention_data.get("text", ""),
        url=mention_data.get("url", ""),
        sentiment=sentiment["sentiment"],
        sentiment_score=sentiment["score"],
        influence_score=mention_data.get("influence_score"),
        reach_estimate=mention_data.get("reach_estimate", 0),
        language=mention_data.get("language", ""),
        media_urls=mention_data.get("media_urls", []),
        mentioned_at=mention_data.get("created_at", timezone.now()),
    )

    alert = check_alerts(mention)

    return {
        "mention_id": str(mention.id),
        "sentiment": sentiment,
        "alert": alert,
    }


def get_mention_summary(
    tenant_id: str,
    days: int = 7,
    tracked_term: str | None = None,
) -> dict[str, Any]:
    """Get summary statistics for mentions.

    :param tenant_id: Tenant scope.
    :param days: Lookback period.
    :param tracked_term: Optional term filter.
    :returns: Summary dict with counts, sentiment distribution.
    """
    since = timezone.now() - timedelta(days=days)
    qs = SocialMention.objects.filter(
        tenant_id=tenant_id, mentioned_at__gte=since
    )
    if tracked_term:
        qs = qs.filter(tracked_term__iexact=tracked_term)

    total = qs.count()
    positive = qs.filter(sentiment="positive").count()
    negative = qs.filter(sentiment="negative").count()
    neutral = qs.filter(sentiment="neutral").count()
    alerts = qs.filter(is_alert_triggered=True).count()

    by_platform: dict[str, int] = {}
    for p in qs.values("platform").distinct():
        platform = p["platform"]
        by_platform[platform] = qs.filter(platform=platform).count()

    by_term: dict[str, int] = {}
    for t in qs.values("tracked_term").distinct():
        term = t["tracked_term"]
        by_term[term] = qs.filter(tracked_term=term).count()

    return {
        "total_mentions": total,
        "sentiment_distribution": {
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
        },
        "alert_count": alerts,
        "by_platform": by_platform,
        "by_tracked_term": by_term,
        "period_days": days,
    }


def filter_mentions(
    tenant_id: str,
    filters: dict[str, Any],
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Filter mentions by multiple criteria.

    :param tenant_id: Tenant scope.
    :param filters: Filter dict with platform, sentiment, term, etc.
    :param limit: Max results.
    :returns: List of mention dicts.
    """
    qs = SocialMention.objects.filter(tenant_id=tenant_id)

    if filters.get("platform"):
        qs = qs.filter(platform=filters["platform"])
    if filters.get("sentiment"):
        qs = qs.filter(sentiment=filters["sentiment"])
    if filters.get("tracked_term"):
        qs = qs.filter(tracked_term__iexact=filters["tracked_term"])
    if filters.get("mention_type"):
        qs = qs.filter(mention_type=filters["mention_type"])
    if filters.get("alerts_only"):
        qs = qs.filter(is_alert_triggered=True)
    if filters.get("since"):
        qs = qs.filter(mentioned_at__gte=filters["since"])

    qs = qs.order_by("-mentioned_at")[:limit]

    return [
        {
            "id": str(m.id),
            "platform": m.platform,
            "tracked_term": m.tracked_term,
            "author_name": m.author_name,
            "text": m.text,
            "sentiment": m.sentiment,
            "sentiment_score": float(m.sentiment_score) if m.sentiment_score else 0,
            "influence_score": float(m.influence_score) if m.influence_score else 0,
            "url": m.url,
            "is_alert_triggered": m.is_alert_triggered,
            "mentioned_at": m.mentioned_at.isoformat(),
        }
        for m in qs
    ]
