"""Keyword research views.

API endpoints for keyword research, semantic clustering,
and opportunity scoring.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.seo.models.keyword import Keyword, KeywordCluster
from apps.seo.serializers import (
    KeywordClusterResponse,
    KeywordResearchRequest,
    KeywordResearchResponse,
    KeywordResponse,
)
from apps.seo.services.keywords import research_keywords

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())


def _kw_to_schema(kw: Keyword) -> KeywordResponse:
    """Convert a Keyword model to a response schema."""
    return KeywordResponse(
        id=str(kw.id),
        keyword=kw.keyword,
        location=kw.location,
        language=kw.language,
        monthlyVolume=kw.monthly_volume,
        difficulty=float(kw.difficulty) if kw.difficulty else None,
        cpc=float(kw.cpc) if kw.cpc else None,
        trendDirection=kw.trend_direction or "",
        trendGrowth=float(kw.trend_growth) if kw.trend_growth else 0.0,
        currentPosition=kw.current_position,
        previousPosition=kw.previous_position,
        opportunityScore=float(kw.opportunity_score) if kw.opportunity_score else 0.0,
        commercialIntent=kw.commercial_intent or "",
        targetUrl=kw.target_url or "",
        isTracked=kw.is_tracked,
        createdAt=kw.created_at,
    )


def _cluster_to_schema(c: dict[str, Any]) -> KeywordClusterResponse:
    """Convert a cluster dict to a response schema."""
    return KeywordClusterResponse(
        label=c["label"],
        keywordCount=c["keyword_count"],
        totalVolume=c["total_volume"],
        avgDifficulty=c["avg_difficulty"],
        priorityScore=c["priority_score"],
    )


@router.post("/keywords/research", response=KeywordResearchResponse, tags=["SEO Keywords"])
def research_keywords_endpoint(request, data: KeywordResearchRequest) -> dict[str, Any]:
    """Research keywords with semantic expansion, filtering, and clustering.

    Takes seed keywords and returns expanded results with opportunity scores.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    filters = data.filters.model_dump(exclude_none=True) if data.filters else {}

    result = research_keywords(
        tenant_id=tenant_id,
        seed_keywords=data.seedKeywords,
        location=data.location,
        language=data.language,
        limit=data.limit,
        filters=filters,
    )

    return {
        "keywords": [_kw_to_schema(kw) for kw in result["keywords"]],
        "clusters": [_cluster_to_schema(c) for c in result["clusters"]],
        "totalFound": result["total_found"],
        "afterFiltering": result["after_filtering"],
        "location": result["location"],
        "language": result["language"],
    }


@router.get("/keywords", response=list[KeywordResponse], tags=["SEO Keywords"])
def list_keywords(
    request,
    limit: int = 100,
    tracked_only: bool = False,
) -> list[KeywordResponse]:
    """List keywords for the tenant.

    Query parameters:
        limit: Maximum results.
        tracked_only: Only return tracked keywords.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    qs = Keyword.objects.filter(tenant_id=tenant_id)
    if tracked_only:
        qs = qs.filter(is_tracked=True)
    return [_kw_to_schema(kw) for kw in qs[:limit]]


@router.get("/keywords/{keyword_id}", response=KeywordResponse, tags=["SEO Keywords"])
def get_keyword(request, keyword_id: str) -> KeywordResponse:
    """Get a single keyword by ID."""
    tenant_id = getattr(request, "tenant_id", "default")
    kw = get_object_or_404(Keyword, id=keyword_id, tenant_id=tenant_id)
    return _kw_to_schema(kw)


@router.get("/keywords/clusters", response=list[KeywordClusterResponse], tags=["SEO Keywords"])
def list_clusters(
    request,
    limit: int = 50,
) -> list[KeywordClusterResponse]:
    """List keyword clusters for the tenant."""
    tenant_id = getattr(request, "tenant_id", "default")
    clusters = KeywordCluster.objects.filter(tenant_id=tenant_id)[:limit]
    return [
        KeywordClusterResponse(
            label=c.label,
            keywordCount=c.keywords.count(),
            totalVolume=c.total_volume,
            avgDifficulty=float(c.avg_difficulty),
            priorityScore=float(c.priority_score),
        )
        for c in clusters
    ]


@router.post("/keywords/{keyword_id}/track", tags=["SEO Keywords"])
def track_keyword(request, keyword_id: str) -> dict[str, Any]:
    """Enable rank tracking for a keyword."""
    tenant_id = getattr(request, "tenant_id", "default")
    kw = get_object_or_404(Keyword, id=keyword_id, tenant_id=tenant_id)
    kw.is_tracked = True
    kw.tracked_at = __import__("django.utils.timezone", fromlist=["timezone"]).now()
    kw.save(update_fields=["is_tracked", "tracked_at"])
    return {"status": "ok", "keyword_id": keyword_id, "is_tracked": True}


@router.delete("/keywords/{keyword_id}/track", tags=["SEO Keywords"])
def untrack_keyword(request, keyword_id: str) -> dict[str, Any]:
    """Disable rank tracking for a keyword."""
    tenant_id = getattr(request, "tenant_id", "default")
    kw = get_object_or_404(Keyword, id=keyword_id, tenant_id=tenant_id)
    kw.is_tracked = False
    kw.save(update_fields=["is_tracked"])
    return {"status": "ok", "keyword_id": keyword_id, "is_tracked": False}
