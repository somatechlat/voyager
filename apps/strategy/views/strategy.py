"""Content Strategy views — SP-003.

CRUD endpoints, topic cluster generation, format mix optimization,
and goal-to-content mapping.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Query, Router

from apps.strategy.models import ContentStrategy
from apps.strategy.serializers.strategy import (
    ContentStrategyIn,
    ContentStrategyOut,
    FormatMixIn,
    FormatMixOut,
    GoalMappingOut,
    StrategyFilter,
    TopicClusterIn,
    TopicClusterOut,
)
from apps.strategy.services.strategy import ContentStrategyService

logger = logging.getLogger(__name__)

router = Router(tags=["Strategy / Content Strategy"])


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


def _strategy_to_dict(s: ContentStrategy) -> dict[str, Any]:
    return {
        "id": str(s.id),
        "name": s.name,
        "goal": s.goal,
        "target_personas": s.target_personas or [],
        "topic_clusters": s.topic_clusters or {},
        "format_mix": s.format_mix or {},
        "channel_allocation": s.channel_allocation or {},
        "content_pillars": s.content_pillars or [],
        "gap_analysis": s.gap_analysis or {},
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@router.post("/strategies", response=ContentStrategyOut)
def create_strategy(request, payload: ContentStrategyIn):
    """Create a new content strategy."""
    tenant_id = _get_tenant_id(request)
    strategy = ContentStrategyService.create_strategy(
        tenant_id=tenant_id,
        name=payload.name,
        goal=payload.goal,
        target_personas=payload.target_personas,
        topic_clusters=payload.topic_clusters,
        format_mix=payload.format_mix,
        channel_allocation=payload.channel_allocation,
        content_pillars=payload.content_pillars,
        gap_analysis=payload.gap_analysis,
    )
    return _strategy_to_dict(strategy)


@router.get("/strategies", response=list[ContentStrategyOut])
def list_strategies(request, filters: Query[StrategyFilter]):
    """List content strategies for the tenant."""
    tenant_id = _get_tenant_id(request)
    qs = ContentStrategy.objects.filter(tenant_id=tenant_id)
    if filters.goal:
        qs = qs.filter(goal=filters.goal)
    if filters.search:
        qs = qs.filter(name__icontains=filters.search)
    qs = qs.order_by("-updated_at")[filters.offset : filters.offset + filters.limit]
    return [_strategy_to_dict(s) for s in qs]


@router.get("/strategies/{strategy_id}", response=ContentStrategyOut)
def get_strategy(request, strategy_id: str):
    """Get a single content strategy."""
    tenant_id = _get_tenant_id(request)
    strategy = ContentStrategy.objects.get(id=strategy_id, tenant_id=tenant_id)
    return _strategy_to_dict(strategy)


@router.put("/strategies/{strategy_id}", response=ContentStrategyOut)
def update_strategy(request, strategy_id: str, payload: ContentStrategyIn):
    """Update a content strategy."""
    tenant_id = _get_tenant_id(request)
    strategy = ContentStrategy.objects.get(id=strategy_id, tenant_id=tenant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(strategy, field, value)
    strategy.save()
    return _strategy_to_dict(strategy)


@router.delete("/strategies/{strategy_id}")
def delete_strategy(request, strategy_id: str):
    """Delete a content strategy."""
    tenant_id = _get_tenant_id(request)
    strategy = ContentStrategy.objects.get(id=strategy_id, tenant_id=tenant_id)
    strategy.delete()
    return {"success": True, "id": str(strategy_id), "action": "deleted"}


# ---------------------------------------------------------------------------
# Goal Mapping
# ---------------------------------------------------------------------------


@router.get("/strategies/goal-mapping/{goal}", response=GoalMappingOut)
def get_goal_mapping(request, goal: str):
    """Get content type mapping for a marketing goal."""
    mapping = ContentStrategyService.get_goal_mapping(goal)
    return mapping


# ---------------------------------------------------------------------------
# Topic Cluster Generation
# ---------------------------------------------------------------------------


@router.post("/strategies/topic-clusters", response=list[TopicClusterOut])
def generate_topic_clusters(request, payload: TopicClusterIn):
    """Generate topic clusters from seed topics."""
    from apps.strategy.services.personas import PersonaService

    tenant_id = _get_tenant_id(request)
    audience = None
    if payload.persona_id:
        try:
            persona = PersonaService.update_persona(
                persona_id=payload.persona_id,
                tenant_id=tenant_id,
            )
            audience = {
                "demographics": persona.demographics,
                "content_preferences": persona.content_preferences,
            }
        except Exception:
            logger.warning("Failed to load persona demographics", exc_info=True)

    # Build competitor data
    competitor_data = []
    if payload.competitor_ids:
        from apps.strategy.models import CompetitorContent

        for cid in payload.competitor_ids:
            contents = CompetitorContent.objects.filter(competitor_id=cid)
            topics: set[str] = set()
            for c in contents:
                topics.update(c.topics or [])
            competitor_data.append(
                {
                    "competitor_id": cid,
                    "topics": list(topics),
                }
            )

    clusters = ContentStrategyService.generate_topic_clusters(
        seed_topics=payload.seed_topics,
        audience_persona=audience,
        competitor_data=competitor_data,
    )
    return clusters


# ---------------------------------------------------------------------------
# Format Mix Optimization
# ---------------------------------------------------------------------------


@router.post("/strategies/format-mix", response=FormatMixOut)
def optimize_format_mix(request, payload: FormatMixIn):
    """Optimize content format mix for a channel."""
    result = ContentStrategyService.optimize_format_mix(
        channel=payload.channel,
        historical_data=payload.historical_data,
    )
    return {"channel": payload.channel, "recommendations": result}
