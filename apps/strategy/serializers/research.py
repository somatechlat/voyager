"""Market Research serializers — SP-006 schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ninja import Schema


class MarketResearchIn(Schema):
    """Input for creating/updating market research."""
    industry: str
    trends: list[dict[str, Any]] | None = None
    market_size: dict[str, Any] | None = None
    audience_insights: dict[str, Any] | None = None
    competitive_landscape: dict[str, Any] | None = None
    research_date: date | None = None


class MarketResearchOut(Schema):
    """Output for market research."""
    id: str
    industry: str
    trends: list[dict[str, Any]]
    market_size: dict[str, Any]
    audience_insights: dict[str, Any]
    competitive_landscape: dict[str, Any]
    research_date: date
    created_at: datetime


class TrendDetectionIn(Schema):
    """Input for trend detection."""
    industry: str
    sources: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None


class TrendOut(Schema):
    """Output for a detected trend."""
    name: str
    velocity: float
    acceleration: float
    volume: int
    trend_score: float
    stage: str
    sources: list[str]
    daily_counts: dict[str, int]


class ResearchFilter(Schema):
    """Query filters for market research listing."""
    industry: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    limit: int = 20
    offset: int = 0


class CompetitiveLandscapeOut(Schema):
    """Output for competitive landscape aggregation."""
    competitor_count: int
    competitors: list[dict[str, Any]]
    platform_coverage: dict[str, int]
    total_tracked_content: int
