"""Content Strategy serializers — SP-003 schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Schema


class ContentStrategyIn(Schema):
    """Input for creating/updating content strategy."""
    name: str
    goal: str = ""
    target_personas: list[str] | None = None
    topic_clusters: dict[str, Any] | None = None
    format_mix: dict[str, Any] | None = None
    channel_allocation: dict[str, Any] | None = None
    content_pillars: list[dict[str, Any]] | None = None
    gap_analysis: dict[str, Any] | None = None


class ContentStrategyOut(Schema):
    """Output for content strategy."""
    id: str
    name: str
    goal: str
    target_personas: list[str]
    topic_clusters: dict[str, Any]
    format_mix: dict[str, Any]
    channel_allocation: dict[str, Any]
    content_pillars: list[dict[str, Any]]
    gap_analysis: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class GoalMappingOut(Schema):
    """Output for goal-to-content mapping."""
    primary: list[str]
    secondary: list[str]
    kpi: list[str]


class TopicClusterIn(Schema):
    """Input for topic cluster generation."""
    seed_topics: list[str]
    persona_id: str | None = None
    competitor_ids: list[str] | None = None


class TopicClusterOut(Schema):
    """Output for topic cluster."""
    pillar: dict[str, Any]
    clusters: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    total_search_volume: int
    avg_difficulty: float
    gap_count: int


class FormatMixIn(Schema):
    """Input for format mix optimization."""
    channel: str
    historical_data: list[dict[str, Any]] | None = None


class FormatMixOut(Schema):
    """Output for format mix recommendation."""
    channel: str
    recommendations: dict[str, float]


class StrategyFilter(Schema):
    """Query filters for strategy listing."""
    goal: str | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0
