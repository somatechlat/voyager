"""Competitor serializers — SP-002 schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class SocialProfilesIn(Schema):
    """Social media profiles input."""

    instagram: dict[str, Any] | None = None
    linkedin: dict[str, Any] | None = None
    twitter: dict[str, Any] | None = None
    tiktok: dict[str, Any] | None = None
    youtube: dict[str, Any] | None = None


class ScrapingConfigIn(Schema):
    """Scraping configuration input."""

    frequency: str = "weekly"
    sources: list[str] | None = None


class CompetitorIn(Schema):
    """Input for creating/updating a competitor."""

    name: str
    website: str = ""
    social_profiles: dict[str, Any] | None = None
    scraping_config: dict[str, Any] | None = None


class CompetitorOut(Schema):
    """Output for a competitor profile."""

    id: str
    name: str
    website: str
    social_profiles: dict[str, Any]
    scraping_config: dict[str, Any]
    last_scraped_at: datetime | None
    is_active: bool
    swot_analysis: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CompetitorContentIn(Schema):
    """Input for adding competitor content."""

    platform: str
    content_type: str
    text: str = ""
    media_urls: list[str] | None = None
    engagement_metrics: dict[str, Any] | None = None
    published_at: str | None = None
    topics: list[str] | None = None
    sentiment: float | None = None


class CompetitorContentOut(Schema):
    """Output for competitor content."""

    id: str
    competitor_id: str
    platform: str
    content_type: str
    text: str
    media_urls: list[str]
    engagement_metrics: dict[str, Any]
    published_at: datetime | None
    topics: list[str]
    sentiment: Decimal | None
    created_at: datetime


class ThemeOut(Schema):
    """Output for an extracted content theme."""

    name: str
    keywords: list[str]
    prevalence: float
    trend: str
    avg_engagement: float
    avg_reach: float
    content_count: int
    trend_over_time: dict[str, int]


class SWOTOut(Schema):
    """Output for SWOT analysis."""

    strengths: list[dict[str, Any]]
    weaknesses: list[dict[str, Any]]
    opportunities: list[dict[str, Any]]
    threats: list[dict[str, Any]]


class CompetitorFilter(Schema):
    """Query filters for competitor listing."""

    is_active: bool | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0
