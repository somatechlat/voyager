"""Pydantic schemas for Content Creation API.

All Ninja request/response models are defined here following the spec
type-by-type.  Each model maps to one or more Django models and
validates at the API boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema
from pydantic import Field


# ---------------------------------------------------------------------------
# Base schemas
# ---------------------------------------------------------------------------


class ContentGenerationOut(Schema):
    """Read-only representation of a content generation."""

    id: UUID
    title: str
    prompt: str
    content_type: str
    status: str
    body_text: str = ""
    media_urls: list[str] = Field(default_factory=list)
    model_used: str = ""
    tokens_used: int | None = None
    generation_time_ms: int | None = None
    brand_kit_id: UUID | None = None
    template_id: UUID | None = None
    created_by: str = ""
    tenant_id: str = ""
    readability_score: float | None = None
    engagement_prediction: float | None = None
    brand_compliance_score: float | None = None
    seo_score: float | None = None
    language: str = "en"
    created_at: datetime
    updated_at: datetime


class GenerateContentIn(Schema):
    """Request body for content generation (text)."""

    brief: str = Field(..., min_length=10, max_length=5000)
    content_type: str = "social_post"
    platforms: list[str] = Field(default_factory=list)
    brand_kit_id: UUID | None = None
    tone: str = "professional"
    language: str = "en"
    max_length: int | None = None
    seo_keywords: list[str] = Field(default_factory=list)
    include_cta: bool = True
    cta_type: str = "auto"
    variations: int = Field(default=1, ge=1, le=5)
    audience_cluster_id: UUID | None = None
    campaign_id: UUID | None = None
    performance_weighting: bool = True
    title: str = ""


class GenerateImageIn(Schema):
    """Request body for image generation."""

    prompt: str = Field(..., min_length=10, max_length=2000)
    style: str = "photographic"
    model: str = "auto"
    aspect_ratio: str = "1:1"
    platform: str | None = None
    brand_kit_id: UUID | None = None
    color_palette: list[str] = Field(default_factory=list)
    text_overlay: dict[str, Any] = Field(default_factory=dict)
    variations: int = Field(default=1, ge=1, le=4)
    negative_prompt: str = ""
    quality: str = "standard"
    remove_background: bool = False
    title: str = ""


class GenerateVideoIn(Schema):
    """Request body for video generation."""

    script: str = Field(..., min_length=50, max_length=10000)
    platform: str
    voice_id: str = "default"
    music_genre: str = "corporate"
    subtitle_language: str = "en"
    style: str = "modern"
    duration: str = "auto"
    brand_kit_id: UUID | None = None
    title: str = ""


class GenerationResponseOut(Schema):
    """Unified response for any generation request."""

    id: UUID
    status: str
    content_type: str
    body_text: str = ""
    media_urls: list[str] = Field(default_factory=list)
    model_used: str = ""
    tokens_used: int = 0
    generation_time_ms: int = 0
    scores: dict[str, float] = Field(default_factory=dict)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    platforms: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


# ---------------------------------------------------------------------------
# Brand Kit schemas
# ---------------------------------------------------------------------------


class BrandKitOut(Schema):
    """Read-only representation of a brand kit."""

    id: UUID
    name: str
    description: str = ""
    voice: str
    tone_rules: list[dict[str, Any]] = Field(default_factory=list)
    forbidden_words: list[str] = Field(default_factory=list)
    required_phrases: list[str] = Field(default_factory=list)
    color_palette: list[dict[str, Any]] = Field(default_factory=list)
    logo_url: str = ""
    font_preferences: dict[str, Any] = Field(default_factory=dict)
    competitor_list: list[str] = Field(default_factory=list)
    avoid_topics: list[str] = Field(default_factory=list)
    target_audience: dict[str, Any] = Field(default_factory=dict)
    min_readability: float = 60.0
    min_compliance_score: int = 75
    tenant_id: str = ""
    created_at: datetime
    updated_at: datetime


class BrandKitIn(Schema):
    """Request body for creating / updating a brand kit."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    voice: str = "professional"
    tone_rules: list[dict[str, Any]] = Field(default_factory=list)
    forbidden_words: list[str] = Field(default_factory=list)
    required_phrases: list[str] = Field(default_factory=list)
    color_palette: list[dict[str, Any]] = Field(default_factory=list)
    logo_url: str = ""
    font_preferences: dict[str, Any] = Field(default_factory=dict)
    competitor_list: list[str] = Field(default_factory=list)
    avoid_topics: list[str] = Field(default_factory=list)
    target_audience: dict[str, Any] = Field(default_factory=dict)
    min_readability: float = 60.0
    min_compliance_score: int = 75


# ---------------------------------------------------------------------------
# Template schemas
# ---------------------------------------------------------------------------


class ContentTemplateOut(Schema):
    """Read-only representation of a content template."""

    id: UUID
    name: str
    description: str = ""
    category: str
    content_type: str
    body: str
    variables: list[dict[str, Any]] = Field(default_factory=list)
    default_values: dict[str, Any] = Field(default_factory=dict)
    brand_kit_id: UUID | None = None
    usage_count: int = 0
    is_public: bool = False
    created_by: str = ""
    tenant_id: str = ""
    created_at: datetime
    updated_at: datetime


class ContentTemplateIn(Schema):
    """Request body for creating / updating a template."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    category: str = "social"
    content_type: str = "text"
    body: str = ""
    variables: list[dict[str, Any]] = Field(default_factory=list)
    default_values: dict[str, Any] = Field(default_factory=dict)
    brand_kit_id: UUID | None = None


class RenderTemplateIn(Schema):
    """Request body for rendering a template with variables."""

    variables: dict[str, Any] = Field(default_factory=dict)
    platform: str | None = None
    brand_kit_id: UUID | None = None


class RenderTemplateOut(Schema):
    """Response for template rendering."""

    rendered: str = ""
    warnings: list[str] = Field(default_factory=list)
    character_count: int = 0


# ---------------------------------------------------------------------------
# A/B Test schemas
# ---------------------------------------------------------------------------


class ABTestOut(Schema):
    """Read-only representation of an A/B test."""

    id: UUID
    name: str
    content_generation_id: UUID
    variants: list[dict[str, Any]] = Field(default_factory=list)
    status: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    sample_size: int | None = None
    winner_criteria: str
    results: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = ""
    created_at: datetime


class ABTestIn(Schema):
    """Request body for creating an A/B test."""

    name: str = Field(..., min_length=1, max_length=255)
    content_generation_id: UUID
    variants: list[dict[str, Any]] = Field(default_factory=list)
    sample_size: int | None = None
    winner_criteria: str = "ctr"
    start_date: datetime | None = None
    end_date: datetime | None = None


class WinnerOut(Schema):
    """Response for A/B test winner calculation."""

    winner: dict[str, Any] | None = None
    confidence: float = 0.0
    significant: bool = False
    message: str = ""
    p_value: float = 0.0


# ---------------------------------------------------------------------------
# Revision schemas
# ---------------------------------------------------------------------------


class RevisionOut(Schema):
    """Read-only representation of a revision."""

    id: UUID
    content_generation_id: UUID
    version_number: int
    diff_json: dict[str, Any] = Field(default_factory=dict)
    body_text: str = ""
    changed_by: str = ""
    change_summary: str = ""
    created_at: datetime


class CreateRevisionIn(Schema):
    """Request body for creating a revision."""

    body_text: str
    changed_by: str
    change_summary: str = ""


# ---------------------------------------------------------------------------
# Repurposing schemas
# ---------------------------------------------------------------------------


class RepurposeIn(Schema):
    """Request body for content repurposing."""

    target_formats: list[str] = Field(default_factory=list)
    transformation_rules: dict[str, Any] = Field(default_factory=dict)


class RepurposeOut(Schema):
    """Response for content repurposing."""

    source_format: str = ""
    target_format: str = ""
    transformed_text: str = ""
    character_count: int = 0
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Compliance / Brand enforcement schemas
# ---------------------------------------------------------------------------


class ComplianceOut(Schema):
    """Response for brand compliance check."""

    score: float = 0.0
    grade: str = "F"
    compliant: bool = False
    violations: list[dict[str, Any]] = Field(default_factory=list)
