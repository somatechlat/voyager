"""Calendar views for drag-and-drop scheduling and conflict detection."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Router

from apps.rbac.auth import VoyagerKeycloakBearer

from ..services.calendar import (
    detect_conflicts,
    get_calendar_day_view,
    get_calendar_month_view,
    get_calendar_posts,
    is_blackout,
    reschedule_post,
)

router = Router(auth=VoyagerKeycloakBearer())


class RescheduleIn:
    """Input for drag-and-drop reschedule."""

    new_datetime: str
    queue_mode: str = "manual"  # auto or manual


@router.get("/calendar/day", response=dict, tags=["Publishing Calendar"])
def calendar_day(
    request,
    date: str = "",
    platform: str = "",
    status: str = "",
) -> dict[str, Any]:
    """Get day view calendar data."""
    tenant_id = getattr(request, "tenant_id", "default")
    filters: dict[str, Any] = {}
    if platform:
        filters["platforms"] = platform.split(",")
    if status:
        filters["status"] = status.split(",")

    if date:
        dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
    else:
        from django.utils import timezone

        dt = timezone.now()

    return get_calendar_day_view(tenant_id, dt, filters)


@router.get("/calendar/month", response=dict, tags=["Publishing Calendar"])
def calendar_month(
    request,
    year: int = 0,
    month: int = 0,
    platform: str = "",
    status: str = "",
) -> dict[str, Any]:
    """Get month view calendar data."""
    tenant_id = getattr(request, "tenant_id", "default")
    filters: dict[str, Any] = {}
    if platform:
        filters["platforms"] = platform.split(",")
    if status:
        filters["status"] = status.split(",")

    if year == 0 or month == 0:
        from django.utils import timezone

        now = timezone.now()
        year = now.year if year == 0 else year
        month = now.month if month == 0 else month

    return get_calendar_month_view(tenant_id, year, month, filters)


@router.get("/calendar/posts", response=list, tags=["Publishing Calendar"])
def calendar_posts(
    request,
    start: str,
    end: str,
    platform: str = "",
    status: str = "",
) -> list[dict[str, Any]]:
    """Get calendar posts in a date range."""
    tenant_id = getattr(request, "tenant_id", "default")
    filters: dict[str, Any] = {}
    if platform:
        filters["platforms"] = platform.split(",")
    if status:
        filters["status"] = status.split(",")

    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))

    return get_calendar_posts(tenant_id, start_dt, end_dt, filters)


@router.post("/calendar/posts/{post_id}/reschedule", response=dict, tags=["Publishing Calendar"])
def reschedule(request, post_id: str, payload: RescheduleIn) -> dict[str, Any]:
    """Reschedule a post via drag-and-drop."""
    tenant_id = getattr(request, "tenant_id", "default")
    new_dt = datetime.fromisoformat(payload.new_datetime.replace("Z", "+00:00"))
    return reschedule_post(tenant_id, post_id, new_dt, payload.queue_mode)


@router.get("/calendar/conflicts", response=list, tags=["Publishing Calendar"])
def conflicts(
    request,
    platform: str,
    account_id: str,
    scheduled_at: str,
    window: int = 30,
) -> list[dict[str, Any]]:
    """Detect scheduling conflicts."""
    tenant_id = getattr(request, "tenant_id", "default")
    dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    return detect_conflicts(tenant_id, platform, account_id, dt, window)


@router.get("/calendar/blackout", response=dict, tags=["Publishing Calendar"])
def blackout_check(
    request,
    scheduled_at: str,
    account_id: str = "",
    platform: str = "",
) -> dict[str, Any]:
    """Check if datetime is in a blackout window."""
    dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    acc_id = account_id or None
    return is_blackout(dt, acc_id, platform)
