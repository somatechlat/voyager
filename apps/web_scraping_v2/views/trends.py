"""Trend detection API endpoints."""

from __future__ import annotations

import logging

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from ..models import TrendDetection
from ..serializers import (
    TrendDetectionCreateSchema,
    TrendDetectionListResponse,
    TrendDetectionSchema,
)
from ..services.trends import TrendAnalyzer

logger = logging.getLogger(__name__)


def create_trend_detection(
    request: HttpRequest,
    payload: TrendDetectionCreateSchema,
) -> TrendDetectionSchema:
    """Create a trend detection from data points.

    Args:
        request: HTTP request.
        payload: Trend detection creation data with data points.

    Returns:
        The created trend detection record.

    Raises:
        HttpError: 400 if topic is empty or data points are invalid.
    """
    if not payload.topic:
        raise HttpError(400, "Topic is required")

    analyzer = TrendAnalyzer()
    trend = analyzer.detect_trends_for_tenant(
        tenant_id=payload.tenant_id,
        topic=payload.topic,
        source=payload.source,
        data_points=payload.data_points,
        industry_baseline=payload.industry_baseline,
    )

    return TrendDetectionSchema(
        id=trend.id,
        tenant_id=trend.tenant_id,
        topic=trend.topic,
        source=trend.source,
        mention_count=trend.mention_count,
        trend_score=trend.trend_score,
        velocity=trend.velocity,
        acceleration=trend.acceleration,
        stage=trend.stage,
        peak_date=trend.peak_date,
        estimated_lifespan_days=trend.estimated_lifespan_days,
        industry_baseline=trend.industry_baseline,
        data_points=trend.data_points,
        tracked_at=trend.tracked_at,
    )


def list_trend_detections(
    request: HttpRequest,
    tenant_id: str = Query("", description="Filter by tenant"),
    topic: str = Query("", description="Filter by topic"),
    stage: str = Query("", description="Filter by stage"),
    source: str = Query("", description="Filter by source"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TrendDetectionListResponse:
    """List trend detections with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Optional tenant filter.
        topic: Optional topic filter.
        stage: Optional stage filter.
        source: Optional source filter.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated trend detection list.
    """
    qs = TrendDetection.objects.all()

    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if topic:
        qs = qs.filter(topic__icontains=topic)
    if stage:
        qs = qs.filter(stage=stage)
    if source:
        qs = qs.filter(source=source)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-tracked_at")[start:end]

    return TrendDetectionListResponse(
        items=[
            TrendDetectionSchema(
                id=t.id,
                tenant_id=t.tenant_id,
                topic=t.topic,
                source=t.source,
                mention_count=t.mention_count,
                trend_score=t.trend_score,
                velocity=t.velocity,
                acceleration=t.acceleration,
                stage=t.stage,
                peak_date=t.peak_date,
                estimated_lifespan_days=t.estimated_lifespan_days,
                industry_baseline=t.industry_baseline,
                data_points=t.data_points,
                tracked_at=t.tracked_at,
            )
            for t in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
