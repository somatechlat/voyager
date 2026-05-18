"""Content optimization views.

API endpoints for NLP-powered content analysis, readability scoring,
keyword density analysis, and optimization recommendations.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.seo.models.content import ContentOptimization
from apps.seo.serializers import (
    ContentOptimizationResponse,
    ContentOptimizeRequest,
    ContentRecommendation,
)
from apps.seo.services.content_opt import optimize_content

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())


def _content_to_schema(opt: ContentOptimization) -> ContentOptimizationResponse:
    """Convert ContentOptimization model to response schema."""
    recommendations = [
        ContentRecommendation(
            type=r.get("type", ""),
            priority=r.get("priority", "medium"),
            description=r.get("description", ""),
            details=r.get("details"),
        )
        for r in (opt.recommendations_json or [])
    ]
    return ContentOptimizationResponse(
        id=str(opt.id),
        url=opt.url or "",
        wordCount=opt.word_count,
        fleschReadingEase=float(opt.flesch_reading_ease) if opt.flesch_reading_ease else None,
        fleschKincaidGrade=float(opt.flesch_kincaid_grade) if opt.flesch_kincaid_grade else None,
        smogIndex=float(opt.smog_index) if opt.smog_index else None,
        keywordDensity=opt.keyword_density_json or {},
        lsiKeywords=opt.lsi_keywords_json or [],
        contentScore=float(opt.content_score) if opt.content_score else None,
        readabilityScore=float(opt.readability_score) if opt.readability_score else None,
        seoScore=float(opt.seo_score) if opt.seo_score else None,
        missingTopics=opt.missing_topics_json or [],
        recommendations=recommendations,
        suggestedTitle=opt.suggested_title or "",
        suggestedMetaDescription=opt.suggested_meta_description or "",
        analyzedAt=opt.analyzed_at,
    )


@router.post("/content/optimize", response=ContentOptimizationResponse, tags=["SEO Content"])
def optimize_content_endpoint(request, data: ContentOptimizeRequest) -> ContentOptimizationResponse:
    """Analyze and optimize content for SEO.

    Provides readability scoring, keyword density analysis,
    LSI keyword extraction, topic gap detection, and recommendations.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    opt = optimize_content(
        tenant_id=tenant_id,
        content=data.content,
        url=data.url,
        target_keywords=data.targetKeywords or [],
        competitor_content=data.competitorContent or [],
    )
    return _content_to_schema(opt)


@router.get(
    "/content/optimizations", response=list[ContentOptimizationResponse], tags=["SEO Content"]
)
def list_optimizations(
    request,
    limit: int = 50,
    url_filter: str = "",
) -> list[ContentOptimizationResponse]:
    """List content optimization results for the tenant.

    Query parameters:
        limit: Maximum results.
        url_filter: Filter by URL substring.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    qs = ContentOptimization.objects.filter(tenant_id=tenant_id)
    if url_filter:
        qs = qs.filter(url__icontains=url_filter)
    return [_content_to_schema(o) for o in qs[:limit]]


@router.get(
    "/content/optimizations/{opt_id}",
    response=ContentOptimizationResponse,
    tags=["SEO Content"],
)
def get_optimization(request, opt_id: str) -> ContentOptimizationResponse:
    """Get a single content optimization result by ID."""
    tenant_id = getattr(request, "tenant_id", "default")
    opt = get_object_or_404(ContentOptimization, id=opt_id, tenant_id=tenant_id)
    return _content_to_schema(opt)


@router.get("/content/optimizations/{opt_id}/recommendations", tags=["SEO Content"])
def get_recommendations(request, opt_id: str) -> dict[str, Any]:
    """Get recommendations for a content optimization."""
    tenant_id = getattr(request, "tenant_id", "default")
    opt = get_object_or_404(ContentOptimization, id=opt_id, tenant_id=tenant_id)
    return {
        "id": str(opt.id),
        "url": opt.url,
        "recommendations": opt.recommendations_json or [],
        "suggested_title": opt.suggested_title,
        "suggested_meta_description": opt.suggested_meta_description,
        "missing_topics": opt.missing_topics_json or [],
    }
