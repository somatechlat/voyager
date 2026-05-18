"""Django Ninja schemas for the Web Scraping v2 module.

Defines request/response models for scrape jobs, competitor monitoring,
price tracking, trend detection, sentiment analysis, SERP tracking, and OCR.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from ninja import Schema


# ---------------------------------------------------------------------------
# Pagination base
# ---------------------------------------------------------------------------


class PaginatedResponse(Schema):
    """Base paginated response."""

    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# ScrapeJob schemas
# ---------------------------------------------------------------------------


class ScrapeJobCreateSchema(Schema):
    """Request body for creating a scrape job."""

    url: str
    selector: str = ""
    tenant_id: str = ""


class ScrapeJobSchema(Schema):
    """Scrape job response."""

    id: UUID
    tenant_id: str
    url: str
    selector: str
    proxy_used: str
    status: str
    content_text: str = ""
    content_html: str = ""
    metadata: dict[str, Any] = {}
    error_message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ScrapeJobListResponse(PaginatedResponse):
    """Paginated scrape job list."""

    items: list[ScrapeJobSchema]


# ---------------------------------------------------------------------------
# CompetitorMonitor schemas
# ---------------------------------------------------------------------------


class CompetitorMonitorCreateSchema(Schema):
    """Request body for creating a competitor monitor."""

    name: str
    url: str
    check_interval_minutes: int = 60
    tenant_id: str = ""


class CompetitorMonitorUpdateSchema(Schema):
    """Request body for updating a competitor monitor."""

    name: str | None = None
    url: str | None = None
    check_interval_minutes: int | None = None
    is_active: bool | None = None


class CompetitorMonitorSchema(Schema):
    """Competitor monitor response."""

    id: UUID
    tenant_id: str
    name: str
    url: str
    check_interval_minutes: int
    is_active: bool
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CompetitorMonitorListResponse(PaginatedResponse):
    """Paginated competitor monitor list."""

    items: list[CompetitorMonitorSchema]


class CompetitorSnapshotSchema(Schema):
    """Competitor snapshot response."""

    id: UUID
    competitor_id: UUID
    url: str
    content_hash: str
    content_text: str = ""
    dom_structure: dict[str, Any] = {}
    screenshot_path: str = ""
    prices: list[dict[str, Any]] = []
    products: list[str] = []
    scraped_at: datetime


class CompetitorChangeSchema(Schema):
    """Competitor change response."""

    id: UUID
    competitor_id: UUID
    url: str
    change_type: str
    change_details: dict[str, Any] = {}
    detected_at: datetime


class CompetitorDetectResponse(Schema):
    """Change detection response."""

    changed: bool
    changes: list[dict[str, Any]] = []
    snapshot_id: UUID | None = None
    reason: str = ""


# ---------------------------------------------------------------------------
# PriceTrack schemas
# ---------------------------------------------------------------------------


class PriceTrackCreateSchema(Schema):
    """Request body for creating a price track."""

    competitor_name: str
    product_name: str
    product_url: str = ""
    price: Decimal
    currency: str = "USD"
    original_price: Decimal | None = None
    tenant_id: str = ""


class PriceTrackSchema(Schema):
    """Price track response."""

    id: UUID
    tenant_id: str
    competitor_name: str
    product_name: str
    product_url: str
    price: Decimal
    currency: str
    original_price: Decimal | None = None
    discount_pct: Decimal | None = None
    normalized_price: Decimal | None = None
    normalized_currency: str
    extraction_source: str
    tracked_at: datetime


class PriceTrackListResponse(PaginatedResponse):
    """Paginated price track list."""

    items: list[PriceTrackSchema]


class PriceNormalizeSchema(Schema):
    """Price normalization request."""

    amount: Decimal
    from_currency: str
    to_currency: str = "USD"


class PriceNormalizeResponse(Schema):
    """Price normalization response."""

    amount: Decimal
    currency: str
    rate: Decimal | None = None
    original: dict[str, Any]


# ---------------------------------------------------------------------------
# TrendDetection schemas
# ---------------------------------------------------------------------------


class TrendDetectionCreateSchema(Schema):
    """Request body for creating a trend detection."""

    topic: str
    source: str = "auto"
    data_points: list[dict[str, Any]] = []
    industry_baseline: int = 0
    tenant_id: str = ""


class TrendDetectionSchema(Schema):
    """Trend detection response."""

    id: UUID
    tenant_id: str
    topic: str
    source: str
    mention_count: int
    trend_score: Decimal
    velocity: Decimal
    acceleration: Decimal
    stage: str
    peak_date: datetime | None = None
    estimated_lifespan_days: int | None = None
    industry_baseline: int
    data_points: list[dict[str, Any]] = []
    tracked_at: datetime


class TrendDetectionListResponse(PaginatedResponse):
    """Paginated trend detection list."""

    items: list[TrendDetectionSchema]


# ---------------------------------------------------------------------------
# SocialMention schemas
# ---------------------------------------------------------------------------


class SocialMentionCreateSchema(Schema):
    """Request body for creating a social mention."""

    brand: str
    platform: str
    author: str = ""
    text: str
    url: str = ""
    engagement: dict[str, Any] = {}
    published_at: datetime | None = None
    tenant_id: str = ""


class SocialMentionSchema(Schema):
    """Social mention response."""

    id: UUID
    tenant_id: str
    brand: str
    platform: str
    author: str
    text: str
    url: str
    fingerprint: str
    sentiment: str = ""
    sentiment_score: Decimal | None = None
    engagement: dict[str, Any] = {}
    cross_platforms: list[str] = []
    published_at: datetime | None = None
    collected_at: datetime


class SocialMentionListResponse(PaginatedResponse):
    """Paginated social mention list."""

    items: list[SocialMentionSchema]


class ShareOfVoiceSchema(Schema):
    """Share of voice request."""

    brand: str
    competitors: list[str] = []
    days: int = 30
    tenant_id: str = ""


class ShareOfVoiceResponse(Schema):
    """Share of voice response."""

    brand: dict[str, Any]
    competitors: list[dict[str, Any]]
    total_mentions: int


# ---------------------------------------------------------------------------
# SentimentScore schemas
# ---------------------------------------------------------------------------


class SentimentAnalyzeSchema(Schema):
    """Request body for sentiment analysis."""

    text: str
    model: str = "auto"
    tenant_id: str = ""
    source_type: str = ""
    source_id: str = ""


class AspectSentimentSchema(Schema):
    """Aspect-based sentiment detail."""

    aspect: str
    sentiment: str
    mentions: int
    score: Decimal


class SentimentScoreSchema(Schema):
    """Sentiment score response."""

    id: UUID
    tenant_id: str
    text: str
    text_hash: str
    source_type: str
    source_id: str
    model: str
    overall_sentiment: str
    overall_score: Decimal
    confidence: Decimal
    aspects: list[dict[str, Any]] = []
    emotions: dict[str, Any] = {}
    language: str
    analyzed_at: datetime


class SentimentScoreListResponse(PaginatedResponse):
    """Paginated sentiment score list."""

    items: list[SentimentScoreSchema]


class SentimentResultSchema(Schema):
    """Inline sentiment analysis result (not persisted)."""

    overall: dict[str, Any]
    aspects: list[dict[str, Any]]
    emotions: dict[str, Any]
    model: str
    language: str


# ---------------------------------------------------------------------------
# SERPTracking schemas
# ---------------------------------------------------------------------------


class SERPTrackSchema(Schema):
    """Request body for SERP tracking."""

    keyword: str
    location_country: str = "us"
    location_region: str = ""
    language: str = "en"
    device: str = "desktop"
    target_url: str = ""
    tenant_id: str = ""


class SERPTrackBatchSchema(Schema):
    """Request body for batch SERP tracking."""

    keywords: list[str]
    location_country: str = "us"
    device: str = "desktop"
    tenant_id: str = ""


class SERPOrganicResultSchema(Schema):
    """Organic SERP result item."""

    position: int
    url: str
    title: str
    description: str


class SERPTrackingSchema(Schema):
    """SERP tracking response."""

    id: UUID
    tenant_id: str
    keyword: str
    location_country: str
    location_region: str
    language: str
    device: str
    position: int | None = None
    url: str
    title: str
    description: str
    serp_features: list[str] = []
    position_change: int
    tracked_at: datetime


class SERPTrackingListResponse(PaginatedResponse):
    """Paginated SERP tracking list."""

    items: list[SERPTrackingSchema]


class SERPTrackResultSchema(Schema):
    """Inline SERP tracking result."""

    keyword: str
    location_country: str
    device: str
    organic_results: list[dict[str, Any]]
    features: list[str]
    position: int | None = None
    position_change: int
    result_count: int


# ---------------------------------------------------------------------------
# OCRJob schemas
# ---------------------------------------------------------------------------


class OCRJobCreateSchema(Schema):
    """Request body for creating an OCR job."""

    file_url: str
    file_type: str = "image"
    languages: str = "eng"
    tenant_id: str = ""


class OCRJobSchema(Schema):
    """OCR job response."""

    id: UUID
    tenant_id: str
    file_url: str
    file_type: str
    languages: str
    status: str
    extracted_text: str = ""
    avg_confidence: Decimal | None = None
    word_count: int
    words: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    preprocessing_applied: list[str] = []
    error_message: str = ""
    processing_time_ms: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class OCRJobListResponse(PaginatedResponse):
    """Paginated OCR job list."""

    items: list[OCRJobSchema]


class OCRProcessResponse(Schema):
    """OCR processing result (inline)."""

    text: str
    confidence: Decimal
    word_count: int
    words: list[dict[str, Any]]
    lines: list[dict[str, Any]]
    blocks: list[dict[str, Any]]
    tables: list[dict[str, Any]]
    preprocessing: list[str]
