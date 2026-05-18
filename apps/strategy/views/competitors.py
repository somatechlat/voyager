"""Competitor Analysis views — SP-002.

CRUD endpoints, NLP theme extraction, SWOT generation,
and competitor content management.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Query, Router

from apps.strategy.models import CompetitorContent, CompetitorProfile
from apps.strategy.serializers.competitors import (
    CompetitorContentIn,
    CompetitorContentOut,
    CompetitorFilter,
    CompetitorIn,
    CompetitorOut,
    SWOTOut,
    ThemeOut,
)
from apps.strategy.services.competitors import CompetitorService

logger = logging.getLogger(__name__)

router = Router(tags=["Strategy / Competitors"])


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


def _competitor_to_dict(c: CompetitorProfile) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "name": c.name,
        "website": c.website or "",
        "social_profiles": c.social_profiles or {},
        "scraping_config": c.scraping_config or {},
        "last_scraped_at": c.last_scraped_at,
        "is_active": c.is_active,
        "swot_analysis": c.swot_analysis or {},
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def _content_to_dict(c: CompetitorContent) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "competitor_id": str(c.competitor_id),
        "platform": c.platform,
        "content_type": c.content_type,
        "text": c.text or "",
        "media_urls": c.media_urls or [],
        "engagement_metrics": c.engagement_metrics or {},
        "published_at": c.published_at,
        "topics": c.topics or [],
        "sentiment": c.sentiment,
        "created_at": c.created_at,
    }


@router.post("/competitors", response=CompetitorOut)
def create_competitor(request, payload: CompetitorIn):
    """Create a competitor profile."""
    tenant_id = _get_tenant_id(request)
    profile = CompetitorService.create_profile(
        tenant_id=tenant_id,
        name=payload.name,
        website=payload.website,
        social_profiles=payload.social_profiles,
        scraping_config=payload.scraping_config,
    )
    return _competitor_to_dict(profile)


@router.get("/competitors", response=list[CompetitorOut])
def list_competitors(request, filters: Query[CompetitorFilter]):
    """List competitor profiles for the tenant."""
    tenant_id = _get_tenant_id(request)
    qs = CompetitorProfile.objects.filter(tenant_id=tenant_id)
    if filters.is_active is not None:
        qs = qs.filter(is_active=filters.is_active)
    if filters.search:
        qs = qs.filter(name__icontains=filters.search)
    qs = qs.order_by("-created_at")[filters.offset : filters.offset + filters.limit]
    return [_competitor_to_dict(c) for c in qs]


@router.get("/competitors/{competitor_id}", response=CompetitorOut)
def get_competitor(request, competitor_id: str):
    """Get a single competitor profile."""
    tenant_id = _get_tenant_id(request)
    profile = CompetitorProfile.objects.get(id=competitor_id, tenant_id=tenant_id)
    return _competitor_to_dict(profile)


@router.put("/competitors/{competitor_id}", response=CompetitorOut)
def update_competitor(request, competitor_id: str, payload: CompetitorIn):
    """Update a competitor profile."""
    tenant_id = _get_tenant_id(request)
    profile = CompetitorProfile.objects.get(id=competitor_id, tenant_id=tenant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    profile.save()
    return _competitor_to_dict(profile)


@router.delete("/competitors/{competitor_id}")
def delete_competitor(request, competitor_id: str):
    """Deactivate a competitor profile."""
    tenant_id = _get_tenant_id(request)
    profile = CompetitorProfile.objects.get(id=competitor_id, tenant_id=tenant_id)
    profile.is_active = False
    profile.save(update_fields=["is_active", "updated_at"])
    return {"success": True, "id": str(competitor_id), "action": "deactivated"}


# ---------------------------------------------------------------------------
# Competitor Content
# ---------------------------------------------------------------------------


@router.post("/competitors/{competitor_id}/content", response=CompetitorContentOut)
def add_competitor_content(
    request,
    competitor_id: str,
    payload: CompetitorContentIn,
):
    """Add scraped content to a competitor profile."""
    content = CompetitorService.add_content(
        competitor_id=competitor_id,
        platform=payload.platform,
        content_type=payload.content_type,
        text=payload.text,
        media_urls=payload.media_urls,
        engagement_metrics=payload.engagement_metrics,
        published_at=payload.published_at,
    )
    return _content_to_dict(content)


@router.get("/competitors/{competitor_id}/content", response=list[CompetitorContentOut])
def list_competitor_content(
    request,
    competitor_id: str,
    platform: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List content for a competitor."""
    tenant_id = _get_tenant_id(request)
    qs = CompetitorContent.objects.filter(
        competitor_id=competitor_id,
        competitor__tenant_id=tenant_id,
    )
    if platform:
        qs = qs.filter(platform=platform)
    qs = qs.order_by("-published_at")[offset : offset + limit]
    return [_content_to_dict(c) for c in qs]


# ---------------------------------------------------------------------------
# NLP Theme Extraction
# ---------------------------------------------------------------------------


@router.get("/competitors/{competitor_id}/themes", response=list[ThemeOut])
def extract_themes(
    request,
    competitor_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """Extract content themes via NLP analysis."""
    tenant_id = _get_tenant_id(request)
    CompetitorProfile.objects.get(id=competitor_id, tenant_id=tenant_id)
    themes = CompetitorService.extract_themes(
        competitor_id=competitor_id,
        date_from=date_from,
        date_to=date_to,
    )
    return themes


# ---------------------------------------------------------------------------
# SWOT Analysis
# ---------------------------------------------------------------------------


@router.get("/competitors/{competitor_id}/swot", response=SWOTOut)
def generate_swot(
    request,
    competitor_id: str,
    own_engagement_rate: float = 0.03,
    own_content_frequency: float = 10.0,
    own_response_time_hours: float = 2.0,
    own_ad_spend: float = 5000.0,
):
    """Generate SWOT analysis for a competitor."""
    tenant_id = _get_tenant_id(request)
    CompetitorProfile.objects.get(id=competitor_id, tenant_id=tenant_id)
    swot = CompetitorService.generate_swot(
        competitor_id=competitor_id,
        own_engagement_rate=own_engagement_rate,
        own_content_frequency=own_content_frequency,
        own_response_time_hours=own_response_time_hours,
        own_ad_spend=own_ad_spend,
    )
    return swot


@router.post("/competitors/{competitor_id}/swot/save", response=CompetitorOut)
def save_swot(request, competitor_id: str):
    """Save auto-generated SWOT to competitor profile."""
    tenant_id = _get_tenant_id(request)
    profile = CompetitorProfile.objects.get(id=competitor_id, tenant_id=tenant_id)
    swot = CompetitorService.generate_swot(competitor_id=competitor_id)
    profile.swot_analysis = swot
    profile.save(update_fields=["swot_analysis", "updated_at"])
    return _competitor_to_dict(profile)
