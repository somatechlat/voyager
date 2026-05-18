"""SERP tracking API endpoints."""

from __future__ import annotations

import logging

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from ..models import SERPTracking
from ..serializers import (
    SERPTrackBatchSchema,
    SERPTrackResultSchema,
    SERPTrackSchema,
    SERPTrackingListResponse,
    SERPTrackingSchema,
)
from ..services.serp import SERPTracker

logger = logging.getLogger(__name__)


def track_serp(
    request: HttpRequest,
    payload: SERPTrackSchema,
) -> SERPTrackResultSchema:
    """Track SERP rankings for a keyword.

    Args:
        request: HTTP request.
        payload: SERP tracking parameters.

    Returns:
        SERP tracking results.

    Raises:
        HttpError: 400 if keyword is empty.
    """
    if not payload.keyword or not payload.keyword.strip():
        raise HttpError(400, "Keyword is required")

    tracker = SERPTracker()
    result = tracker.track(
        keyword=payload.keyword,
        tenant_id=payload.tenant_id,
        location_country=payload.location_country,
        location_region=payload.location_region,
        language=payload.language,
        device=payload.device,
        target_url=payload.target_url,
    )

    if "error" in result:
        raise HttpError(429, result["error"])

    return SERPTrackResultSchema(
        keyword=result["keyword"],
        location_country=result["location_country"],
        device=result["device"],
        organic_results=result.get("organic_results", []),
        features=result.get("features", []),
        position=result.get("position"),
        position_change=result.get("position_change", 0),
        result_count=result.get("result_count", 0),
    )


def batch_track_serp(
    request: HttpRequest,
    payload: SERPTrackBatchSchema,
) -> list[SERPTrackResultSchema]:
    """Track SERP rankings for multiple keywords.

    Args:
        request: HTTP request.
        payload: Batch SERP tracking parameters.

    Returns:
        List of SERP tracking results.

    Raises:
        HttpError: 400 if keywords list is empty or too large.
    """
    if not payload.keywords:
        raise HttpError(400, "Keywords list is required")
    if len(payload.keywords) > 50:
        raise HttpError(400, "Maximum 50 keywords per batch request")

    tracker = SERPTracker()
    results = tracker.batch_track(
        keywords=payload.keywords,
        tenant_id=payload.tenant_id,
        location_country=payload.location_country,
        device=payload.device,
    )

    return [
        SERPTrackResultSchema(
            keyword=r["keyword"],
            location_country=r.get("location_country", payload.location_country),
            device=r.get("device", payload.device),
            organic_results=r.get("organic_results", []),
            features=r.get("features", []),
            position=r.get("position"),
            position_change=r.get("position_change", 0),
            result_count=r.get("result_count", 0),
        )
        for r in results
        if "error" not in r
    ]


def list_serp_trackings(
    request: HttpRequest,
    tenant_id: str = Query("", description="Filter by tenant"),
    keyword: str = Query("", description="Filter by keyword"),
    device: str = Query("", description="Filter by device"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> SERPTrackingListResponse:
    """List SERP tracking records with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Optional tenant filter.
        keyword: Optional keyword filter.
        device: Optional device filter.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated SERP tracking list.
    """
    qs = SERPTracking.objects.all()

    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if keyword:
        qs = qs.filter(keyword__icontains=keyword)
    if device:
        qs = qs.filter(device=device)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-tracked_at")[start:end]

    return SERPTrackingListResponse(
        items=[
            SERPTrackingSchema(
                id=t.id,
                tenant_id=t.tenant_id,
                keyword=t.keyword,
                location_country=t.location_country,
                location_region=t.location_region,
                language=t.language,
                device=t.device,
                position=t.position,
                url=t.url,
                title=t.title,
                description=t.description,
                serp_features=t.serp_features,
                position_change=t.position_change,
                tracked_at=t.tracked_at,
            )
            for t in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
