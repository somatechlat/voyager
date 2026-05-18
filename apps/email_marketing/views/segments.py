"""Audience segment management views."""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.email_marketing.models.segment import AudienceSegment
from apps.email_marketing.serializers import (
    AudienceSegmentCreateSchema,
    AudienceSegmentDetailSchema,
    AudienceSegmentListSchema,
    AudienceSegmentUpdateSchema,
    SegmentRefreshSchema,
    SubscriberIdsSchema,
)
from apps.email_marketing.services.segments import (
    evaluate_dynamic_segment,
    evaluate_predictive_segment,
    refresh_segment_count,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/", response=list[AudienceSegmentListSchema])
def list_segments(
    request,
    tenant_id: str = "",
    segment_type: str = "",
    search: str = "",
    limit: int = 50,
    offset: int = 0,
) -> list[AudienceSegment]:
    """List audience segments with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        segment_type: Filter by segment type.
        search: Search in name or description.
        limit: Page size.
        offset: Pagination offset.

    Returns:
        List of segments.
    """
    qs = AudienceSegment.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if segment_type:
        qs = qs.filter(segment_type=segment_type)
    if search:
        qs = qs.filter(name__icontains=search) | qs.filter(description__icontains=search)
    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.post("/", response=AudienceSegmentDetailSchema)
def create_segment(
    request,
    payload: AudienceSegmentCreateSchema,
) -> AudienceSegment:
    """Create a new audience segment.

    Args:
        request: HTTP request.
        payload: Segment creation data.

    Returns:
        Created segment.
    """
    data = payload.dict()
    segment = AudienceSegment.objects.create(**data)
    logger.info("Segment %s created for tenant %s", segment.id, segment.tenant_id)
    return segment


@router.get("/{segment_id}", response=AudienceSegmentDetailSchema)
def get_segment(
    request,
    segment_id: int,
) -> AudienceSegment:
    """Get a single audience segment.

    Args:
        request: HTTP request.
        segment_id: Segment primary key.

    Returns:
        Audience segment.
    """
    return get_object_or_404(AudienceSegment, id=segment_id)


@router.put("/{segment_id}", response=AudienceSegmentDetailSchema)
def update_segment(
    request,
    segment_id: int,
    payload: AudienceSegmentUpdateSchema,
) -> AudienceSegment:
    """Update an audience segment.

    Args:
        request: HTTP request.
        segment_id: Segment primary key.
        payload: Update data.

    Returns:
        Updated segment.
    """
    segment = get_object_or_404(AudienceSegment, id=segment_id)
    data = payload.dict(exclude_unset=True)
    for attr, val in data.items():
        setattr(segment, attr, val)
    segment.save()
    return segment


@router.delete("/{segment_id}")
def delete_segment(
    request,
    segment_id: int,
) -> dict[str, bool]:
    """Delete an audience segment.

    Args:
        request: HTTP request.
        segment_id: Segment primary key.

    Returns:
        Success dict.
    """
    segment = get_object_or_404(AudienceSegment, id=segment_id)
    segment.delete()
    return {"success": True}


@router.post("/{segment_id}/refresh")
def refresh_segment(
    request,
    segment_id: int,
) -> dict[str, Any]:
    """Refresh segment subscriber count.

    Args:
        request: HTTP request.
        segment_id: Segment primary key.

    Returns:
        Refresh result with new count.
    """
    segment = get_object_or_404(AudienceSegment, id=segment_id)
    count = refresh_segment_count(segment)
    return {
        "success": True,
        "segment_id": str(segment.id),
        "subscriber_count": count,
        "segment_type": segment.segment_type,
    }


@router.post("/{segment_id}/evaluate")
def evaluate_segment(
    request,
    segment_id: int,
    payload: SegmentRefreshSchema,
) -> dict[str, Any]:
    """Evaluate a segment and return matching subscriber IDs.

    Args:
        request: HTTP request.
        segment_id: Segment primary key.
        payload: Evaluation options.

    Returns:
        Matching subscriber IDs and count.
    """
    segment = get_object_or_404(AudienceSegment, id=segment_id)
    if segment.segment_type == AudienceSegment.Type.PREDICTIVE:
        ids = evaluate_predictive_segment(segment)
    else:
        ids = evaluate_dynamic_segment(segment, limit=payload.limit)
    return {
        "segment_id": str(segment.id),
        "segment_type": segment.segment_type,
        "matching_count": len(ids),
        "subscriber_ids": ids[: payload.limit],
    }


@router.post("/{segment_id}/set-subscribers")
def set_static_subscribers(
    request,
    segment_id: int,
    payload: SubscriberIdsSchema,
) -> dict[str, Any]:
    """Set subscriber IDs for a static segment.

    Args:
        request: HTTP request.
        segment_id: Segment primary key.
        payload: Subscriber IDs list.

    Returns:
        Update result.
    """
    segment = get_object_or_404(AudienceSegment, id=segment_id)
    segment.rules = {"subscriber_ids": payload.subscriber_ids}
    segment.save(update_fields=["rules"])
    count = refresh_segment_count(segment)
    return {
        "success": True,
        "segment_id": str(segment.id),
        "subscriber_count": count,
    }
