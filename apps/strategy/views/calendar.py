"""Editorial Calendar views — SP-004.

CRUD endpoints, calendar views, workload calculation,
and pipeline management.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from ninja import Query, Router

from apps.strategy.models import EditorialCalendar
from apps.strategy.serializers.calendar import (
    CalendarEntryIn,
    CalendarEntryOut,
    CalendarFilter,
    PipelineSummaryOut,
    StatusTransitionIn,
    WorkloadOut,
)
from apps.strategy.services.calendar import CalendarService

logger = logging.getLogger(__name__)

router = Router(tags=["Strategy / Editorial Calendar"])


def _get_tenant_id(request) -> str:
    return getattr(request, "tenant_id", "default")


def _entry_to_dict(entry: EditorialCalendar) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "title": entry.title,
        "content_type": entry.content_type,
        "content_type_label": entry.get_content_type_display(),
        "color_code": entry.color_code,
        "platform": entry.platform or "",
        "status": entry.status,
        "status_label": entry.get_status_display(),
        "publish_date": entry.publish_date,
        "due_date": entry.due_date,
        "assignee_id": str(entry.assignee_id) if entry.assignee_id else None,
        "priority": entry.priority,
        "estimated_hours": float(entry.estimated_hours) if entry.estimated_hours else None,
        "actual_hours": float(entry.actual_hours) if entry.actual_hours else None,
        "notes": entry.notes or "",
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


@router.post("/calendar", response=CalendarEntryOut)
def create_entry(request, payload: CalendarEntryIn):
    """Create a new editorial calendar entry."""
    tenant_id = _get_tenant_id(request)
    entry = CalendarService.create_entry(
        tenant_id=tenant_id,
        title=payload.title,
        content_type=payload.content_type,
        platform=payload.platform,
        strategy_id=payload.strategy_id,
        campaign_id=payload.campaign_id,
        assignee_id=payload.assignee_id,
        due_date=payload.due_date,
        publish_date=payload.publish_date,
        priority=payload.priority,
        estimated_hours=payload.estimated_hours,
        notes=payload.notes,
    )
    return _entry_to_dict(entry)


@router.get("/calendar", response=list[CalendarEntryOut])
def list_entries(request, filters: Query[CalendarFilter]):
    """List calendar entries for the tenant."""
    tenant_id = _get_tenant_id(request)
    qs = EditorialCalendar.objects.filter(tenant_id=tenant_id)
    if filters.status:
        qs = qs.filter(status=filters.status)
    if filters.assignee_id:
        qs = qs.filter(assignee_id=filters.assignee_id)
    if filters.content_type:
        qs = qs.filter(content_type=filters.content_type)
    if filters.campaign_id:
        qs = qs.filter(campaign_id=filters.campaign_id)
    if filters.date_from and filters.date_to:
        qs = qs.filter(publish_date__gte=filters.date_from, publish_date__lte=filters.date_to)
    elif filters.date_from:
        qs = qs.filter(publish_date__gte=filters.date_from)
    elif filters.date_to:
        qs = qs.filter(publish_date__lte=filters.date_to)
    qs = qs.order_by("publish_date", "priority")[filters.offset : filters.offset + filters.limit]
    return [_entry_to_dict(e) for e in qs]


@router.get("/calendar/{entry_id}", response=CalendarEntryOut)
def get_entry(request, entry_id: str):
    """Get a single calendar entry."""
    tenant_id = _get_tenant_id(request)
    entry = EditorialCalendar.objects.get(id=entry_id, tenant_id=tenant_id)
    return _entry_to_dict(entry)


@router.put("/calendar/{entry_id}", response=CalendarEntryOut)
def update_entry(request, entry_id: str, payload: CalendarEntryIn):
    """Update a calendar entry."""
    tenant_id = _get_tenant_id(request)
    entry = EditorialCalendar.objects.get(id=entry_id, tenant_id=tenant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in ("due_date", "publish_date") and value == "":
            value = None
        setattr(entry, field, value)
    entry.save()
    return _entry_to_dict(entry)


@router.delete("/calendar/{entry_id}")
def delete_entry(request, entry_id: str):
    """Delete a calendar entry."""
    tenant_id = _get_tenant_id(request)
    entry = EditorialCalendar.objects.get(id=entry_id, tenant_id=tenant_id)
    entry.delete()
    return {"success": True, "id": str(entry_id), "action": "deleted"}


# ---------------------------------------------------------------------------
# Calendar View (color-coded)
# ---------------------------------------------------------------------------


@router.get("/calendar-view")
def calendar_view(
    request,
    date_from: date,
    date_to: date,
    status: str | None = None,
    assignee_id: str | None = None,
    content_type: str | None = None,
):
    """Get color-coded calendar entries for a date range."""
    tenant_id = _get_tenant_id(request)
    status_filter = [status] if status else None
    return CalendarService.get_calendar_view(
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        status_filter=status_filter,
        assignee_id=assignee_id,
        content_type=content_type,
    )


# ---------------------------------------------------------------------------
# Workload
# ---------------------------------------------------------------------------


@router.get("/calendar/workload/{assignee_id}", response=WorkloadOut)
def get_workload(
    request,
    assignee_id: str,
    date_from: date,
    date_to: date,
):
    """Calculate workload for a team member."""
    tenant_id = _get_tenant_id(request)
    return CalendarService.calculate_workload(
        assignee_id=assignee_id,
        date_from=date_from,
        date_to=date_to,
        tenant_id=tenant_id,
    )


# ---------------------------------------------------------------------------
# Pipeline Management
# ---------------------------------------------------------------------------


@router.post("/calendar/{entry_id}/transition")
def transition_status(
    request,
    entry_id: str,
    payload: StatusTransitionIn,
):
    """Move a calendar entry to a new pipeline stage."""
    tenant_id = _get_tenant_id(request)
    entry = CalendarService.transition_status(
        entry_id=entry_id,
        tenant_id=tenant_id,
        new_status=payload.new_status,
    )
    return _entry_to_dict(entry)


@router.get("/calendar/pipeline/summary", response=PipelineSummaryOut)
def pipeline_summary(request):
    """Get pipeline summary for the tenant."""
    tenant_id = _get_tenant_id(request)
    return CalendarService.get_pipeline_summary(tenant_id=tenant_id)


# ---------------------------------------------------------------------------
# Content Type Colors
# ---------------------------------------------------------------------------


@router.get("/calendar/content-types")
def content_types(request):
    """Get content type definitions with color codes."""
    return [
        {
            "value": choice[0],
            "label": choice[1],
            "color": EditorialCalendar.CONTENT_TYPE_COLORS.get(choice[0], "#6B7280"),
        }
        for choice in EditorialCalendar.ContentType.choices
    ]
