"""Calendar service — conflict detection and calendar data management.

Handles drag-and-drop rescheduling with conflict detection,
blackout window checks, and frequency limit validation.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.db import models
from django.utils import timezone

from ..models import BlackoutWindow, ContentCalendar, ScheduledPost
from .scheduler import PLATFORM_DEFAULTS, get_daily_post_count, get_next_available_slot

logger = logging.getLogger(__name__)

# Status to colour mapping
STATUS_COLORS: dict[str, str] = {
    "draft": "#9CA3AF",
    "pending_approval": "#F59E0B",
    "approved": "#3B82F6",
    "scheduled": "#10B981",
    "publishing": "#8B5CF6",
    "published": "#059669",
    "failed": "#EF4444",
    "cancelled": "#9CA3AF",
}


def get_color_for_status(status: str) -> str:
    """Return hex colour for a post status."""
    return STATUS_COLORS.get(status, "#9CA3AF")


def get_calendar_posts(
    tenant_id: str,
    start: timezone.datetime,
    end: timezone.datetime,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Get scheduled posts for calendar rendering.

    Args:
        tenant_id: Tenant scope.
        start: Start datetime.
        end: End datetime.
        filters: Optional filters (platforms, status, campaigns, etc.).

    Returns:
        List of post dicts with calendar metadata.
    """
    qs = ScheduledPost.objects.filter(
        tenant_id=tenant_id,
        scheduled_at__gte=start,
        scheduled_at__lte=end,
    ).exclude(status=ScheduledPost.Status.CANCELLED)

    if filters:
        if platforms := filters.get("platforms"):
            qs = qs.filter(platform__in=platforms)
        if status_list := filters.get("status"):
            qs = qs.filter(status__in=status_list)
        if campaigns := filters.get("campaigns"):
            qs = qs.filter(campaign_id__in=campaigns)
        if created_by := filters.get("created_by"):
            qs = qs.filter(created_by=created_by)
        if tags := filters.get("tags"):
            for tag in tags:
                qs = qs.filter(tags__contains=[tag])

    posts: list[dict[str, Any]] = []
    for post in qs.select_related("calendar_entry"):
        color = None
        try:
            if post.calendar_entry and post.calendar_entry.color_override:
                color = post.calendar_entry.color_override
        except ContentCalendar.DoesNotExist:
            logger.debug("Calendar entry not found for post")
        if not color:
            color = get_color_for_status(post.status)

        posts.append(
            {
                "id": str(post.id),
                "platform": post.platform,
                "caption": post.caption,
                "scheduled_at": post.scheduled_at.isoformat(),
                "status": post.status,
                "priority": post.priority,
                "color": color,
                "publish_type": post.publish_type,
                "media_count": len(post.media_urls) if post.media_urls else 0,
                "link": post.link or "",
                "account_id": str(post.account_id),
                "campaign_id": str(post.campaign_id) if post.campaign_id else None,
                "tags": post.tags,
            }
        )

    return posts


def detect_conflicts(
    tenant_id: str,
    platform: str,
    account_id: str,
    scheduled_at: timezone.datetime,
    window_minutes: int = 30,
    exclude_post_id: str | None = None,
) -> list[dict[str, Any]]:
    """Find scheduling conflicts within a time window.

    Args:
        tenant_id: Tenant scope.
        platform: Platform name.
        account_id: Account UUID.
        scheduled_at: Target time.
        window_minutes: Conflict window in minutes.
        exclude_post_id: Post to exclude.

    Returns:
        List of conflict dicts.
    """
    from ..models import ScheduledPost

    start = scheduled_at - timedelta(minutes=window_minutes)
    end = scheduled_at + timedelta(minutes=window_minutes)

    qs = ScheduledPost.objects.filter(
        tenant_id=tenant_id,
        platform=platform,
        account_id=account_id,
        scheduled_at__gte=start,
        scheduled_at__lte=end,
    ).exclude(
        status=ScheduledPost.Status.CANCELLED,
    )
    if exclude_post_id:
        qs = qs.exclude(id=exclude_post_id)

    conflicts: list[dict[str, Any]] = []
    for post in qs:
        conflicts.append(
            {
                "id": str(post.id),
                "caption": post.caption,
                "scheduled_at": post.scheduled_at.isoformat(),
                "status": post.status,
                "minutes_away": abs((post.scheduled_at - scheduled_at).total_seconds()) / 60,
            }
        )
    return conflicts


def is_blackout(
    scheduled_at: timezone.datetime,
    account_id: str | None = None,
    platform: str = "",
) -> dict[str, Any]:
    """Check if a datetime falls in a blackout window.

    Args:
        scheduled_at: Time to check.
        account_id: Optional account scope.
        platform: Optional platform scope.

    Returns:
        Dict with is_blackout, reason, and blackout_id.
    """
    windows = (
        BlackoutWindow.objects.filter(
            is_active=True,
            start_at__lte=scheduled_at,
            end_at__gte=scheduled_at,
        )
        .filter(
            models.Q(account_id__isnull=True) | models.Q(account_id=account_id),
        )
        .filter(
            models.Q(platform="") | models.Q(platform=platform),
        )
    )

    for bw in windows:
        if bw.is_blackout(scheduled_at):
            return {
                "is_blackout": True,
                "reason": bw.name,
                "blackout_id": str(bw.id),
                "start_at": bw.start_at.isoformat(),
                "end_at": bw.end_at.isoformat(),
            }

    return {"is_blackout": False}


def reschedule_post(
    tenant_id: str,
    post_id: str,
    new_datetime: timezone.datetime,
    queue_mode: str = "manual",
) -> dict[str, Any]:
    """Reschedule a post with conflict detection.

    Args:
        tenant_id: Tenant scope.
        post_id: ScheduledPost UUID.
        new_datetime: New scheduled time.
        queue_mode: "auto" or "manual" conflict handling.

    Returns:
        Result dict with adjusted, new_time, conflicts, reason.
    """
    try:
        post = ScheduledPost.objects.get(id=post_id, tenant_id=tenant_id)
    except ScheduledPost.DoesNotExist:
        return {"adjusted": False, "reason": "post_not_found", "message": "Post not found"}

    # Conflict detection
    conflicts = detect_conflicts(
        tenant_id,
        post.platform,
        str(post.account_id),
        new_datetime,
        exclude_post_id=post_id,
    )
    if conflicts:
        if queue_mode == "auto":
            adjusted = get_next_available_slot(
                tenant_id,
                post.platform,
                str(post.account_id),
                new_datetime,
            )
            if adjusted:
                post.scheduled_at = adjusted
                post.save(update_fields=["scheduled_at"])
                return {
                    "adjusted": True,
                    "new_time": adjusted.isoformat(),
                    "reason": "conflict_avoided",
                    "original_conflicts": conflicts,
                }
            return {
                "adjusted": False,
                "reason": "no_available_slot",
                "conflicts": conflicts,
            }
        return {
            "adjusted": False,
            "conflicts": conflicts,
            "requires_user_decision": True,
        }

    # Blackout window check
    blackout = is_blackout(new_datetime, str(post.account_id), post.platform)
    if blackout["is_blackout"]:
        return {
            "adjusted": False,
            "reason": "blackout_window",
            "message": f"This date falls in blackout period: {blackout['reason']}",
        }

    # Frequency limit check
    limits = PLATFORM_DEFAULTS.get(post.platform, {"maxPerDay": 3})
    daily_count = get_daily_post_count(tenant_id, post.platform, str(post.account_id), new_datetime)
    if daily_count >= limits["maxPerDay"]:
        return {
            "adjusted": False,
            "reason": "frequency_limit",
            "message": f"Daily limit reached for {post.platform} ({daily_count}/{limits['maxPerDay']})",
        }

    # Execute reschedule
    post.scheduled_at = new_datetime
    post.save(update_fields=["scheduled_at"])

    return {"adjusted": True, "new_time": new_datetime.isoformat()}


def get_calendar_day_view(
    tenant_id: str,
    date: timezone.datetime,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get calendar day view data.

    Args:
        tenant_id: Tenant scope.
        date: Date to render.
        filters: Optional filters.

    Returns:
        Day view data with hourly slots.
    """
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    posts = get_calendar_posts(tenant_id, start, end, filters)

    # Organize into hourly slots (6am - 11pm)
    slots: dict[str, list[dict[str, Any]]] = {}
    for hour in range(6, 24):
        key = f"{hour:02d}:00"
        slots[key] = []

    for post in posts:
        post_dt = timezone.datetime.fromisoformat(post["scheduled_at"])
        hour_key = f"{post_dt.hour:02d}:00"
        if hour_key in slots:
            slots[hour_key].append(post)

    return {"date": start.date().isoformat(), "view": "day", "slots": slots, "total": len(posts)}


def get_calendar_month_view(
    tenant_id: str,
    year: int,
    month: int,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Get calendar month view data.

    Args:
        tenant_id: Tenant scope.
        year: Year number.
        month: Month number (1-12).
        filters: Optional filters.

    Returns:
        Month view data with daily summaries.
    """
    from calendar import monthrange

    start = timezone.datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
    _, last_day = monthrange(year, month)
    end = start + timedelta(days=last_day)
    posts = get_calendar_posts(tenant_id, start, end, filters)

    # Daily summaries
    days: dict[str, dict[str, Any]] = {}
    for day in range(1, last_day + 1):
        day_str = f"{year}-{month:02d}-{day:02d}"
        days[day_str] = {"count": 0, "posts": [], "statuses": {}}

    for post in posts:
        post_dt = timezone.datetime.fromisoformat(post["scheduled_at"])
        day_str = post_dt.date().isoformat()
        if day_str in days:
            days[day_str]["count"] += 1
            days[day_str]["posts"].append(post)
            status = post["status"]
            days[day_str]["statuses"][status] = days[day_str]["statuses"].get(status, 0) + 1

    return {"year": year, "month": month, "view": "month", "days": days, "total": len(posts)}
