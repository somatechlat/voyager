"""Rank tracking views.

API endpoints for SERP position monitoring, feature detection,
ranking history, and change alerts.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.seo.models.keyword import Keyword
from apps.seo.models.rank import RankHistory, SERPTracking
from apps.seo.serializers import (
    RankDistributionResponse,
    RankTrackingCreateRequest,
    RankTrackingResponse,
    RankTrackingUpdateRequest,
    RankTrendResponse,
)
from apps.seo.services.rank_tracking import (
    collect_ranking,
    get_ranking_distribution,
    get_ranking_trend,
)

logger = logging.getLogger(__name__)

router = Router(auth=VoyagerKeycloakBearer())


def _tracking_to_schema(t: SERPTracking) -> RankTrackingResponse:
    """Convert SERPTracking model to response schema."""
    return RankTrackingResponse(
        id=str(t.id),
        keywordId=str(t.keyword_id),
        keyword=t.keyword.keyword if t.keyword else "",
        targetUrl=t.target_url or "",
        device=t.device,
        alertThreshold=t.alert_threshold,
        isActive=t.is_active,
        currentPosition=t.current_position,
        previousPosition=t.previous_position,
        positionChange=t.position_change,
        currentUrl=t.current_url or "",
        serpFeatures=t.serp_features_json or [],
        lastCheckedAt=t.last_checked_at,
        checkCount=t.check_count,
        bestPosition=t.best_position,
        worstPosition=t.worst_position,
        createdAt=t.created_at,
    )


@router.post("/rank-tracking", response=RankTrackingResponse, tags=["SEO Rank Tracking"])
def create_tracking(request, data: RankTrackingCreateRequest) -> RankTrackingResponse:
    """Start tracking a keyword for SERP position monitoring.

    Creates a tracking entry linked to an existing keyword record.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    keyword = get_object_or_404(Keyword, id=data.keywordId, tenant_id=tenant_id)
    tracking = SERPTracking.objects.create(
        tenant_id=tenant_id,
        keyword=keyword,
        target_url=data.targetUrl,
        locations_json=data.locations or ["US"],
        device=data.device,
        alert_threshold=data.alertThreshold,
        is_active=True,
        current_position=keyword.current_position,
    )
    return _tracking_to_schema(tracking)


@router.get("/rank-tracking", response=list[RankTrackingResponse], tags=["SEO Rank Tracking"])
def list_trackings(
    request,
    limit: int = 100,
    active_only: bool = True,
) -> list[RankTrackingResponse]:
    """List rank tracking entries for the tenant.

    Query parameters:
        limit: Maximum results.
        active_only: Only return active trackings.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    qs = SERPTracking.objects.filter(tenant_id=tenant_id)
    if active_only:
        qs = qs.filter(is_active=True)
    return [_tracking_to_schema(t) for t in qs.select_related("keyword")[:limit]]


@router.get(
    "/rank-tracking/{tracking_id}",
    response=RankTrackingResponse,
    tags=["SEO Rank Tracking"],
)
def get_tracking(request, tracking_id: str) -> RankTrackingResponse:
    """Get a single rank tracking entry by ID."""
    tenant_id = getattr(request, "tenant_id", "default")
    tracking = get_object_or_404(SERPTracking, id=tracking_id, tenant_id=tenant_id)
    return _tracking_to_schema(tracking)


@router.post("/rank-tracking/{tracking_id}/update", tags=["SEO Rank Tracking"])
def update_ranking(request, tracking_id: str, data: RankTrackingUpdateRequest) -> dict[str, Any]:
    """Update a ranking for a tracked keyword.

    Records the current position, URL, and SERP features.
    Triggers alerts if the change exceeds the threshold.
    """
    tenant_id = getattr(request, "tenant_id", "default")
    tracking = get_object_or_404(SERPTracking, id=tracking_id, tenant_id=tenant_id)
    result = collect_ranking(
        tracking=tracking,
        position=data.position,
        url=data.url,
        serp_features=data.serpFeatures or [],
        competitors=data.competitors or [],
        page_title=data.pageTitle,
        page_description=data.pageDescription,
        location=data.location,
        device=data.device,
    )
    return result


@router.get(
    "/rank-tracking/{tracking_id}/trend",
    response=list[RankTrendResponse],
    tags=["SEO Rank Tracking"],
)
def get_trend(
    request,
    tracking_id: str,
    days: int = 30,
) -> list[RankTrendResponse]:
    """Get ranking trend for a tracked keyword.

    Query parameters:
        days: Number of days to look back (default 30).
    """
    tenant_id = getattr(request, "tenant_id", "default")
    tracking = get_object_or_404(SERPTracking, id=tracking_id, tenant_id=tenant_id)
    trend = get_ranking_trend(tracking, days=days)
    return [
        RankTrendResponse(
            position=t["position"],
            trackedAt=t["tracked_at"],
            url=t["url"],
            serpFeatures=t["serp_features"] or [],
        )
        for t in trend
    ]


@router.get(
    "/rank-tracking/distribution",
    response=RankDistributionResponse,
    tags=["SEO Rank Tracking"],
)
def ranking_distribution(request) -> dict[str, Any]:
    """Get keyword ranking distribution for the tenant."""
    tenant_id = getattr(request, "tenant_id", "default")
    dist = get_ranking_distribution(tenant_id)
    return dist


@router.delete("/rank-tracking/{tracking_id}", tags=["SEO Rank Tracking"])
def stop_tracking(request, tracking_id: str) -> dict[str, Any]:
    """Stop tracking a keyword (deactivate, not delete)."""
    tenant_id = getattr(request, "tenant_id", "default")
    tracking = get_object_or_404(SERPTracking, id=tracking_id, tenant_id=tenant_id)
    tracking.is_active = False
    tracking.save(update_fields=["is_active"])
    return {"status": "ok", "tracking_id": tracking_id, "is_active": False}


@router.get("/rank-tracking/{tracking_id}/history", tags=["SEO Rank Tracking"])
def get_history(
    request,
    tracking_id: str,
    limit: int = 100,
) -> dict[str, Any]:
    """Get ranking history for a tracked keyword."""
    tenant_id = getattr(request, "tenant_id", "default")
    tracking = get_object_or_404(SERPTracking, id=tracking_id, tenant_id=tenant_id)
    history = (
        RankHistory.objects.filter(tracking=tracking)
        .order_by("-tracked_at")
        .values("position", "previous_position", "position_change", "url", "tracked_at", "device")[
            :limit
        ]
    )
    return {
        "tracking_id": tracking_id,
        "keyword": tracking.keyword.keyword if tracking.keyword else "",
        "history": list(history),
    }
