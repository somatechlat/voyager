"""Keyword research service.

Implements keyword research with semantic expansion, clustering,
opportunity scoring, and commercial intent detection.
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

from django.db.models import Q

from apps.seo.models.keyword import Keyword

logger = logging.getLogger(__name__)

# Question prefixes for keyword expansion
_QUESTION_PREFIXES = ["who", "what", "when", "where", "why", "how", "is", "are", "can", "does"]

# Generic anchor words for intent detection
_INFORMATIONAL = ["how", "what", "why", "when", "where", "who", "guide", "tutorial", "learn"]
_NAVIGATIONAL = ["login", "sign in", "homepage", "website", "official", "app"]
_TRANSACTIONAL = ["buy", "discount", "deal", "coupon", "free shipping", "order"]
_COMMERCIAL = ["best", "top", "review", "compare", "vs", "alternative", "pricing"]


def detect_intent(keyword: str) -> str:
    """Detect the commercial intent of a keyword.

    Args:
        keyword: The keyword phrase to analyze.

    Returns:
        One of ``informational``, ``navigational``, ``commercial``,
        or ``transactional``.
    """
    kw_lower = keyword.lower()
    words = set(kw_lower.split())

    scores = {
        "informational": sum(1 for w in _INFORMATIONAL if w in kw_lower) * 0.3,
        "navigational": sum(1 for w in _NAVIGATIONAL if w in kw_lower) * 0.5,
        "commercial": sum(1 for w in _COMMERCIAL if w in kw_lower) * 0.7,
        "transactional": sum(1 for w in _TRANSACTIONAL if w in kw_lower) * 1.0,
    }

    # Boost for question patterns
    if any(kw_lower.startswith(q + " ") for q in _QUESTION_PREFIXES):
        scores["informational"] += 0.5

    if not scores:
        return "informational"

    return max(scores, key=scores.get)


def calculate_opportunity_score(
    volume: int | None,
    difficulty: float | None,
    intent: str,
    trend_growth: float = 0.0,
    current_rank: int | None = None,
) -> float:
    """Calculate the opportunity score for a keyword.

    Formula::
        log10(volume) * 0.30 + (100 - difficulty) * 0.25 +
        intent_weight * 100 * 0.20 + trend_growth * 100 * 0.15 +
        (current_rank ? (100 - current_rank) * 0.10 : 0)

    Args:
        volume: Monthly search volume.
        difficulty: Keyword difficulty 0-100.
        intent: Detected commercial intent.
        trend_growth: Trend growth rate.
        current_rank: Current SERP position if known.

    Returns:
        Opportunity score as a float.
    """
    vol_score = math.log10(max(volume, 1)) * 0.30 if volume else 0.0
    diff_score = (100.0 - (difficulty or 50.0)) * 0.25

    intent_weights: dict[str, float] = {
        "informational": 0.3,
        "navigational": 0.5,
        "commercial": 0.7,
        "transactional": 1.0,
    }
    intent_score = intent_weights.get(intent, 0.3) * 100.0 * 0.20
    trend_score = trend_growth * 100.0 * 0.15
    rank_score = 0.0
    if current_rank and current_rank > 0:
        rank_score = (100.0 - min(current_rank, 100)) * 0.10

    return vol_score + diff_score + intent_score + trend_score + rank_score


def expand_keywords(seed_keywords: list[str]) -> list[str]:
    """Expand seed keywords with question-based variations.

    Args:
        seed_keywords: List of seed keywords.

    Returns:
        Expanded list including question variations.
    """
    expanded: set[str] = set(seed_keywords)
    for kw in seed_keywords:
        kw_lower = kw.lower()
        for prefix in _QUESTION_PREFIXES:
            expanded.add(f"{prefix} {kw_lower}")
            expanded.add(f"{prefix} to {kw_lower}")
        # Add plural form
        if not kw_lower.endswith("s"):
            expanded.add(f"{kw_lower}s")
        # Add "best" prefix
        expanded.add(f"best {kw_lower}")
        expanded.add(f"{kw_lower} guide")
        expanded.add(f"{kw_lower} tutorial")
    return list(expanded)


def semantic_cluster_keywords(
    keywords: list[Keyword],
) -> list[dict[str, Any]]:
    """Cluster keywords semantically by embedding similarity.

    Uses a simplified greedy clustering approach grouping keywords
    that share 2+ content words.

    Args:
        keywords: List of Keyword objects to cluster.

    Returns:
        List of cluster dicts with label, keywords, total_volume,
        avg_difficulty, and priority_score.
    """
    clusters: list[dict[str, Any]] = []
    assigned: set[str] = set()

    for kw in keywords:
        if str(kw.id) in assigned:
            continue
        kw_words = set(re.findall(r"[a-zA-Z]+", kw.keyword.lower()))
        cluster_kws: list[Keyword] = [kw]
        assigned.add(str(kw.id))

        for other in keywords:
            if str(other.id) in assigned:
                continue
            other_words = set(re.findall(r"[a-zA-Z]+", other.keyword.lower()))
            shared = kw_words & other_words
            if len(shared) >= 2 or (len(shared) == 1 and len(kw_words) <= 2):
                cluster_kws.append(other)
                assigned.add(str(other.id))

        total_volume = sum((k.monthly_volume or 0) for k in cluster_kws)
        avg_difficulty = sum(
            (float(k.difficulty) if k.difficulty else 50.0) for k in cluster_kws
        ) / max(len(cluster_kws), 1)
        priority = total_volume * (1.0 - avg_difficulty / 100.0)

        clusters.append(
            {
                "label": kw.keyword[:50],
                "keywords": cluster_kws,
                "keyword_count": len(cluster_kws),
                "total_volume": total_volume,
                "avg_difficulty": round(avg_difficulty, 2),
                "priority_score": round(max(priority, 0), 4),
            }
        )

    return sorted(clusters, key=lambda c: c["priority_score"], reverse=True)


def research_keywords(
    tenant_id: str,
    seed_keywords: list[str],
    location: str = "US",
    language: str = "en",
    limit: int = 100,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Research keywords with expansion, filtering, clustering, and scoring.

    Args:
        tenant_id: Tenant scope identifier.
        seed_keywords: Starting keywords for research.
        location: ISO country code.
        language: ISO language code.
        limit: Maximum results to return.
        filters: Optional filter criteria.

    Returns:
        Dict with keywords, clusters, total_found, after_filtering.
    """
    filters = filters or {}
    expanded = expand_keywords(seed_keywords)

    # Query existing keywords that match expanded list
    q_filter = Q()
    for kw in expanded:
        q_filter |= Q(keyword__icontains=kw)

    queryset = Keyword.objects.filter(
        q_filter,
        tenant_id=tenant_id,
        location=location,
        language=language,
    )

    # Apply filters
    vol_min = filters.get("volumeMin")
    vol_max = filters.get("volumeMax")
    diff_max = filters.get("difficultyMax")
    cpc_min = filters.get("cpcMin")
    exclude = filters.get("excludeKeywords", [])

    if vol_min is not None:
        queryset = queryset.filter(monthly_volume__gte=vol_min)
    if vol_max is not None:
        queryset = queryset.filter(monthly_volume__lte=vol_max)
    if diff_max is not None:
        queryset = queryset.filter(difficulty__lte=diff_max)
    if cpc_min is not None:
        queryset = queryset.filter(cpc__gte=cpc_min)

    keywords = list(queryset[: limit * 2])

    # Apply exclude filter
    if exclude:
        keywords = [
            k for k in keywords if not any(ex.lower() in k.keyword.lower() for ex in exclude)
        ]

    total_found = len(keywords)

    # Compute intent and opportunity for each
    for kw in keywords:
        intent = detect_intent(kw.keyword)
        kw.commercial_intent = intent
        kw.opportunity_score = calculate_opportunity_score(
            volume=kw.monthly_volume,
            difficulty=float(kw.difficulty) if kw.difficulty else None,
            intent=intent,
            trend_growth=float(kw.trend_growth) if kw.trend_growth else 0.0,
            current_rank=kw.current_position,
        )
        kw.save(update_fields=["commercial_intent", "opportunity_score"])

    # Sort by opportunity score
    keywords.sort(key=lambda k: float(k.opportunity_score or 0), reverse=True)
    keywords = keywords[:limit]

    # Cluster results
    clusters = semantic_cluster_keywords(keywords)

    return {
        "keywords": keywords,
        "clusters": clusters,
        "total_found": total_found,
        "after_filtering": len(keywords),
        "location": location,
        "language": language,
    }
