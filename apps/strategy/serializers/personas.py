"""Persona serializers — SP-001 schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class DemographicsIn(Schema):
    """Demographic input schema."""

    ageRange: dict[str, int] | None = None
    gender: list[str] | None = None
    locations: list[dict[str, Any]] | None = None
    incomeRange: dict[str, Any] | None = None
    education: list[str] | None = None
    occupation: list[str] | None = None
    familyStatus: list[str] | None = None
    languages: list[str] | None = None


class PsychographicsIn(Schema):
    """Psychographic input schema."""

    values: list[str] | None = None
    interests: list[str] | None = None
    lifestyle: list[str] | None = None
    personality: list[str] | None = None
    motivations: list[str] | None = None
    frustrations: list[str] | None = None


class ChannelRankingIn(Schema):
    """Channel preference ranking input."""

    platform: str
    rank: int
    engagementRate: float | None = None
    timeSpent: str | None = None
    openRate: float | None = None
    clickRate: float | None = None
    watchTime: str | None = None


class PersonaIn(Schema):
    """Input for creating/updating a persona."""

    name: str
    description: str = ""
    demographics: dict[str, Any]
    psychographics: dict[str, Any] | None = None
    pain_points: list[str] | None = None
    content_preferences: dict[str, Any] | None = None
    channel_preferences: list[dict[str, Any]] | None = None
    data_sources: list[dict[str, Any]] | None = None


class PersonaOut(Schema):
    """Output for a persona."""

    id: str
    name: str
    description: str
    demographics: dict[str, Any]
    psychographics: dict[str, Any]
    pain_points: list[str]
    content_preferences: dict[str, Any]
    channel_preferences: list[dict[str, Any]]
    data_sources: list[dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PersonaCampaignLinkIn(Schema):
    """Input for linking persona to campaign."""

    campaign_id: str
    weight: float = 0.5


class PersonaCampaignLinkOut(Schema):
    """Output for persona-campaign link."""

    id: str
    persona_id: str
    campaign_id: str
    weight: Decimal
    created_at: datetime


class PersonaFilter(Schema):
    """Query filters for persona listing."""

    is_active: bool | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0


class AggregatedTargetingOut(Schema):
    """Output for aggregated persona targeting."""

    age_range: dict[str, int | None]
    gender: list[str]
    languages: list[str]
    locations: list[dict[str, Any]]
    persona_count: int
