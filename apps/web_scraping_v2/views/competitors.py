"""Competitor monitoring API endpoints."""

from __future__ import annotations

import logging
from uuid import UUID

from django.http import HttpRequest
from ninja import Query
from ninja.errors import HttpError

from ..models import CompetitorChange, CompetitorMonitor, CompetitorSnapshot
from ..serializers import (
    CompetitorChangeSchema,
    CompetitorDetectResponse,
    CompetitorMonitorCreateSchema,
    CompetitorMonitorListResponse,
    CompetitorMonitorSchema,
    CompetitorMonitorUpdateSchema,
    CompetitorSnapshotSchema,
)
from ..services.competitors import CompetitorAnalyzer

logger = logging.getLogger(__name__)


def create_competitor_monitor(
    request: HttpRequest,
    payload: CompetitorMonitorCreateSchema,
) -> CompetitorMonitorSchema:
    """Create a new competitor monitor.

    Args:
        request: HTTP request.
        payload: Competitor monitor creation data.

    Returns:
        The created competitor monitor.

    Raises:
        HttpError: 400 if URL is invalid.
    """
    if not payload.url.startswith(("http://", "https://")):
        raise HttpError(400, "Invalid URL: must start with http:// or https://")

    monitor = CompetitorMonitor.objects.create(
        tenant_id=payload.tenant_id,
        name=payload.name,
        url=payload.url,
        check_interval_minutes=payload.check_interval_minutes,
    )

    return CompetitorMonitorSchema(
        id=monitor.id,
        tenant_id=monitor.tenant_id,
        name=monitor.name,
        url=monitor.url,
        check_interval_minutes=monitor.check_interval_minutes,
        is_active=monitor.is_active,
        last_checked_at=monitor.last_checked_at,
        created_at=monitor.created_at,
        updated_at=monitor.updated_at,
    )


def detect_changes(
    request: HttpRequest,
    monitor_id: UUID,
) -> CompetitorDetectResponse:
    """Run change detection for a competitor monitor.

    Args:
        request: HTTP request.
        monitor_id: UUID of the competitor monitor.

    Returns:
        Change detection results.

    Raises:
        HttpError: 404 if monitor not found.
    """
    try:
        monitor = CompetitorMonitor.objects.get(id=monitor_id)
    except CompetitorMonitor.DoesNotExist:
        raise HttpError(404, f"Competitor monitor {monitor_id} not found")

    analyzer = CompetitorAnalyzer()
    result = analyzer.detect_changes(monitor)

    snapshot_id = None
    if result.get("snapshot_id"):
        from uuid import UUID as _UUID

        snapshot_id = _UUID(result["snapshot_id"])

    return CompetitorDetectResponse(
        changed=result.get("changed", False),
        changes=result.get("changes", []),
        snapshot_id=snapshot_id,
        reason=result.get("reason", ""),
    )


def list_competitors(
    request: HttpRequest,
    tenant_id: str = Query("", description="Filter by tenant"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CompetitorMonitorListResponse:
    """List competitor monitors.

    Args:
        request: HTTP request.
        tenant_id: Optional tenant filter.
        is_active: Optional active status filter.
        page: Page number (1-indexed).
        page_size: Items per page.

    Returns:
        Paginated competitor monitor list.
    """
    qs = CompetitorMonitor.objects.all()

    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-created_at")[start:end]

    return CompetitorMonitorListResponse(
        items=[
            CompetitorMonitorSchema(
                id=m.id,
                tenant_id=m.tenant_id,
                name=m.name,
                url=m.url,
                check_interval_minutes=m.check_interval_minutes,
                is_active=m.is_active,
                last_checked_at=m.last_checked_at,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def list_snapshots(
    request: HttpRequest,
    monitor_id: UUID,
    limit: int = Query(20, ge=1, le=100),
) -> list[CompetitorSnapshotSchema]:
    """List snapshots for a competitor monitor.

    Args:
        request: HTTP request.
        monitor_id: UUID of the competitor monitor.
        limit: Maximum number of snapshots to return.

    Returns:
        List of competitor snapshots.

    Raises:
        HttpError: 404 if monitor not found.
    """
    try:
        monitor = CompetitorMonitor.objects.get(id=monitor_id)
    except CompetitorMonitor.DoesNotExist:
        raise HttpError(404, f"Competitor monitor {monitor_id} not found")

    snapshots = (
        CompetitorSnapshot.objects.filter(competitor=monitor)
        .order_by("-scraped_at")[:limit]
    )

    return [
        CompetitorSnapshotSchema(
            id=s.id,
            competitor_id=s.competitor_id,
            url=s.url,
            content_hash=s.content_hash,
            content_text=s.content_text,
            dom_structure=s.dom_structure,
            screenshot_path=s.screenshot_path,
            prices=s.prices,
            products=s.products,
            scraped_at=s.scraped_at,
        )
        for s in snapshots
    ]


def list_changes(
    request: HttpRequest,
    monitor_id: UUID,
    limit: int = Query(50, ge=1, le=200),
) -> list[CompetitorChangeSchema]:
    """List detected changes for a competitor monitor.

    Args:
        request: HTTP request.
        monitor_id: UUID of the competitor monitor.
        limit: Maximum number of changes to return.

    Returns:
        List of competitor changes.

    Raises:
        HttpError: 404 if monitor not found.
    """
    try:
        monitor = CompetitorMonitor.objects.get(id=monitor_id)
    except CompetitorMonitor.DoesNotExist:
        raise HttpError(404, f"Competitor monitor {monitor_id} not found")

    changes = (
        CompetitorChange.objects.filter(competitor=monitor)
        .order_by("-detected_at")[:limit]
    )

    return [
        CompetitorChangeSchema(
            id=c.id,
            competitor_id=c.competitor_id,
            url=c.url,
            change_type=c.change_type,
            change_details=c.change_details,
            detected_at=c.detected_at,
        )
        for c in changes
    ]
