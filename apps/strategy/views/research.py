"""Market Research views — SP-006.

CRUD endpoints, trend detection, market sizing,
and competitive landscape aggregation.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Query, Router

from apps.strategy.models import MarketResearch
from apps.strategy.serializers.research import (
    CompetitiveLandscapeOut,
    MarketResearchIn,
    MarketResearchOut,
    ResearchFilter,
    TrendDetectionIn,
    TrendOut,
)
from apps.strategy.services.research import ResearchService

logger = logging.getLogger(__name__)

router = Router(tags=["Strategy / Market Research"])


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


def _research_to_dict(r: MarketResearch) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "industry": r.industry,
        "trends": r.trends or [],
        "market_size": r.market_size or {},
        "audience_insights": r.audience_insights or {},
        "competitive_landscape": r.competitive_landscape or {},
        "research_date": r.research_date,
        "created_at": r.created_at,
    }


@router.post("/research", response=MarketResearchOut)
def create_research(request, payload: MarketResearchIn):
    """Create a market research entry."""
    tenant_id = _get_tenant_id(request)
    entry = ResearchService.create_research(
        tenant_id=tenant_id,
        industry=payload.industry,
        trends=payload.trends,
        market_size=payload.market_size,
        audience_insights=payload.audience_insights,
        competitive_landscape=payload.competitive_landscape,
        research_date=payload.research_date,
    )
    return _research_to_dict(entry)


@router.get("/research", response=list[MarketResearchOut])
def list_research(request, filters: Query[ResearchFilter]):
    """List market research entries for the tenant."""
    tenant_id = _get_tenant_id(request)
    qs = MarketResearch.objects.filter(tenant_id=tenant_id)
    if filters.industry:
        qs = qs.filter(industry__icontains=filters.industry)
    if filters.date_from:
        qs = qs.filter(research_date__gte=filters.date_from)
    if filters.date_to:
        qs = qs.filter(research_date__lte=filters.date_to)
    qs = qs.order_by("-research_date")[filters.offset : filters.offset + filters.limit]
    return [_research_to_dict(r) for r in qs]


@router.get("/research/{research_id}", response=MarketResearchOut)
def get_research(request, research_id: str):
    """Get a single market research entry."""
    tenant_id = _get_tenant_id(request)
    entry = MarketResearch.objects.get(id=research_id, tenant_id=tenant_id)
    return _research_to_dict(entry)


@router.put("/research/{research_id}", response=MarketResearchOut)
def update_research(request, research_id: str, payload: MarketResearchIn):
    """Update a market research entry."""
    tenant_id = _get_tenant_id(request)
    entry = MarketResearch.objects.get(id=research_id, tenant_id=tenant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    entry.save()
    return _research_to_dict(entry)


@router.delete("/research/{research_id}")
def delete_research(request, research_id: str):
    """Delete a market research entry."""
    tenant_id = _get_tenant_id(request)
    entry = MarketResearch.objects.get(id=research_id, tenant_id=tenant_id)
    entry.delete()
    return {"success": True, "id": str(research_id), "action": "deleted"}


# ---------------------------------------------------------------------------
# Trend Detection
# ---------------------------------------------------------------------------


@router.post("/research/detect-trends", response=list[TrendOut])
def detect_trends(request, payload: TrendDetectionIn):
    """Detect trends from competitor data."""
    tenant_id = _get_tenant_id(request)
    return ResearchService.detect_trends(
        tenant_id=tenant_id,
        industry=payload.industry,
        sources=payload.sources,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )


# ---------------------------------------------------------------------------
# Market Size
# ---------------------------------------------------------------------------


@router.get("/research/market-size")
def estimate_market_size(
    request,
    industry: str,
    geo_scope: str = "global",
):
    """Estimate market size (TAM/SAM/SOM)."""
    return ResearchService.estimate_market_size(
        industry=industry,
        geo_scope=geo_scope,
    )


# ---------------------------------------------------------------------------
# Competitive Landscape
# ---------------------------------------------------------------------------


@router.get("/research/competitive-landscape", response=CompetitiveLandscapeOut)
def competitive_landscape(request):
    """Get aggregated competitive landscape from tracked competitors."""
    tenant_id = _get_tenant_id(request)
    return ResearchService.aggregate_competitive_landscape(tenant_id=tenant_id)
