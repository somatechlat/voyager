"""Celery tasks for the Strategy module.

Handles strategic planning workflows, market analysis, competitive
intelligence processing, OKR data sync, and trend detection.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def analyze_market_position(
    self,
    tenant_id: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Analyze market position for a tenant.

    Args:
        tenant_id: UUID of the tenant scope.
        parameters: Analysis parameters including industry and sources.

    Returns:
        Result dict with analysis output.
    """
    logger.info("Analyzing market position for tenant %s", tenant_id)

    from apps.strategy.services.research import ResearchService

    industry = parameters.get("industry", "general")
    sources = parameters.get("sources", ["social_media", "news"])

    trends = ResearchService.detect_trends(
        tenant_id=tenant_id,
        industry=industry,
        sources=sources,
    )
    landscape = ResearchService.aggregate_competitive_landscape(
        tenant_id=tenant_id,
    )

    return {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "industry": industry,
        "trends_detected": len(trends),
        "competitors_tracked": landscape.get("competitor_count", 0),
        "top_trends": [t["name"] for t in trends[:5]],
    }


@shared_task(bind=True, max_retries=3)
def extract_competitor_themes(
    self,
    competitor_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Run NLP theme extraction on competitor content.

    Args:
        competitor_id: UUID of the competitor.
        date_from: Optional start date (ISO format).
        date_to: Optional end date (ISO format).

    Returns:
        Result with extracted themes and their metrics.
    """
    logger.info("Extracting themes for competitor %s", competitor_id)

    from apps.strategy.services.competitors import CompetitorService

    themes = CompetitorService.extract_themes(
        competitor_id=competitor_id,
        date_from=date_from,
        date_to=date_to,
    )

    return {
        "status": "ok",
        "task": self.name,
        "competitor_id": competitor_id,
        "themes_found": len(themes),
        "themes": [
            {
                "name": t["name"],
                "keywords": t["keywords"],
                "prevalence": t["prevalence"],
                "trend": t["trend"],
                "content_count": t["content_count"],
            }
            for t in themes
        ],
    }


@shared_task(bind=True, max_retries=3)
def generate_swot_analysis(
    self,
    competitor_id: str,
    own_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate and save SWOT analysis for a competitor.

    Args:
        competitor_id: UUID of the competitor.
        own_metrics: Own brand metrics for comparison.

    Returns:
        SWOT analysis result.
    """
    logger.info("Generating SWOT for competitor %s", competitor_id)

    from apps.strategy.models import CompetitorProfile
    from apps.strategy.services.competitors import CompetitorService

    own = own_metrics or {}
    swot = CompetitorService.generate_swot(
        competitor_id=competitor_id,
        own_engagement_rate=own.get("engagement_rate", 0.03),
        own_content_frequency=own.get("content_frequency", 10.0),
        own_response_time_hours=own.get("response_time_hours", 2.0),
        own_ad_spend=own.get("ad_spend", 5000.0),
        own_topics=own.get("topics", []),
    )

    # Save to profile
    try:
        profile = CompetitorProfile.objects.get(id=competitor_id)
        profile.swot_analysis = swot
        profile.save(update_fields=["swot_analysis", "updated_at"])
    except CompetitorProfile.DoesNotExist:
        logger.warning("Competitor %s not found for SWOT save", competitor_id)

    return {
        "status": "ok",
        "task": self.name,
        "competitor_id": competitor_id,
        "swot": swot,
    }


@shared_task(bind=True, max_retries=3)
def generate_topic_clusters(
    self,
    tenant_id: str,
    seed_topics: list[str],
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate topic clusters for content strategy.

    Args:
        tenant_id: UUID of the tenant.
        seed_topics: Root pillar topics.
        parameters: Optional config (persona_id, competitor_ids).

    Returns:
        Generated clusters with gaps and metrics.
    """
    logger.info("Generating topic clusters for tenant %s: %s", tenant_id, seed_topics)

    from apps.strategy.services.strategy import ContentStrategyService

    params = parameters or {}
    clusters = ContentStrategyService.generate_topic_clusters(
        seed_topics=seed_topics,
        audience_persona=params.get("audience_persona"),
        competitor_data=params.get("competitor_data", []),
        own_content_topics=params.get("own_content_topics", []),
    )

    return {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "seed_topics": seed_topics,
        "clusters_generated": len(clusters),
        "clusters": [
            {
                "pillar": c["pillar"],
                "cluster_count": len(c["clusters"]),
                "gaps": len(c["gaps"]),
                "total_search_volume": c["total_search_volume"],
                "avg_difficulty": c["avg_difficulty"],
            }
            for c in clusters
        ],
    }


@shared_task(bind=True, max_retries=3)
def sync_okr_data_sources(
    self,
    tenant_id: str,
    quarter: str | None = None,
) -> dict[str, Any]:
    """Sync all OKR key results with external data sources.

    Args:
        tenant_id: UUID of the tenant.
        quarter: Optional quarter filter (e.g. '2026-Q2').

    Returns:
        Sync results per key result.
    """
    logger.info("Syncing OKR data sources for tenant %s", tenant_id)

    from apps.strategy.models.okr import KeyResult, Objective
    from apps.strategy.services.okr import OKRService

    qs = Objective.objects.filter(tenant_id=tenant_id)
    if quarter:
        qs = qs.filter(quarter=quarter)

    synced = 0
    for obj in qs:
        for kr in obj.key_results.all():
            if kr.data_source:
                try:
                    # In production: fetch from actual analytics API
                    current = float(kr.current_value)
                    OKRService.update_progress(
                        key_result_id=str(kr.id),
                        current_value=current,
                    )
                    synced += 1
                except Exception as exc:
                    logger.warning("Failed to sync KR %s: %s", kr.id, exc)

    return {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "synced_count": synced,
        "quarter": quarter,
    }


@shared_task(bind=True, max_retries=3)
def detect_market_trends(
    self,
    tenant_id: str,
    industry: str,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect market trends and save research entry.

    Args:
        tenant_id: UUID of the tenant.
        industry: Industry to analyze.
        parameters: Optional config (sources, date range).

    Returns:
        Trend detection results.
    """
    logger.info("Detecting trends for %s / tenant %s", industry, tenant_id)

    from datetime import date

    from apps.strategy.services.research import ResearchService

    params = parameters or {}
    trends = ResearchService.detect_trends(
        tenant_id=tenant_id,
        industry=industry,
        sources=params.get("sources"),
        date_from=params.get("date_from"),
        date_to=params.get("date_to"),
    )

    # Save research entry
    ResearchService.create_research(
        tenant_id=tenant_id,
        industry=industry,
        trends=trends,
        research_date=params.get("research_date", date.today()),
    )

    return {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "industry": industry,
        "trends_found": len(trends),
        "top_trends": [
            {
                "name": t["name"],
                "score": t["trend_score"],
                "stage": t["stage"],
            }
            for t in trends[:10]
        ],
    }


@shared_task(bind=True, max_retries=3)
def refresh_competitive_landscape(
    self,
    tenant_id: str,
) -> dict[str, Any]:
    """Refresh the competitive landscape for a tenant.

    Args:
        tenant_id: UUID of the tenant.

    Returns:
        Landscape refresh results.
    """
    logger.info("Refreshing competitive landscape for tenant %s", tenant_id)

    from apps.strategy.services.research import ResearchService

    landscape = ResearchService.aggregate_competitive_landscape(tenant_id=tenant_id)

    return {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "competitors": landscape.get("competitor_count", 0),
        "platforms": landscape.get("platform_coverage", {}),
        "content_tracked": landscape.get("total_tracked_content", 0),
    }
