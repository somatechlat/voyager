"""Sentiment analysis API endpoints."""

from __future__ import annotations

import logging

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from ..models import SentimentScore
from ..serializers import (
    SentimentAnalyzeSchema,
    SentimentResultSchema,
    SentimentScoreListResponse,
    SentimentScoreSchema,
)
from ..services.sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)


def analyze_sentiment_text(
    request: HttpRequest,
    payload: SentimentAnalyzeSchema,
) -> SentimentResultSchema:
    """Analyze sentiment of provided text.

    Args:
        request: HTTP request.
        payload: Sentiment analysis request with text and model preference.

    Returns:
        Sentiment analysis result.

    Raises:
        HttpError: 400 if text is missing.
    """
    if not payload.text or not payload.text.strip():
        raise HttpError(400, "Text is required for sentiment analysis")

    analyzer = SentimentAnalyzer()
    result = analyzer.analyze(
        text=payload.text,
        model=payload.model,
        tenant_id=payload.tenant_id,
        source_type=payload.source_type,
        source_id=payload.source_id,
    )

    return SentimentResultSchema(
        overall=result["overall"],
        aspects=result["aspects"],
        emotions=result["emotions"],
        model=result["model"],
        language=result["language"],
    )


def list_sentiment_scores(
    request: HttpRequest,
    tenant_id: str = Query("", description="Filter by tenant"),
    sentiment: str = Query("", description="Filter by sentiment"),
    model: str = Query("", description="Filter by model"),
    days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SentimentScoreListResponse:
    """List sentiment scores with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Optional tenant filter.
        sentiment: Optional sentiment filter.
        model: Optional model filter.
        days: Number of days to look back.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated sentiment score list.
    """
    from django.utils import timezone
    from datetime import timedelta

    qs = SentimentScore.objects.filter(
        analyzed_at__gte=timezone.now() - timedelta(days=days)
    )

    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if sentiment:
        qs = qs.filter(overall_sentiment=sentiment)
    if model:
        qs = qs.filter(model=model)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-analyzed_at")[start:end]

    return SentimentScoreListResponse(
        items=[
            SentimentScoreSchema(
                id=s.id,
                tenant_id=s.tenant_id,
                text=s.text[:500],
                text_hash=s.text_hash,
                source_type=s.source_type,
                source_id=s.source_id,
                model=s.model,
                overall_sentiment=s.overall_sentiment,
                overall_score=s.overall_score,
                confidence=s.confidence,
                aspects=s.aspects,
                emotions=s.emotions,
                language=s.language,
                analyzed_at=s.analyzed_at,
            )
            for s in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
