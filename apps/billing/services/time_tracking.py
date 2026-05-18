"""Time tracking service.

Handles timer modes (timer/manual/automatic/calendar), rounding rules,
timesheet validation, and approval workflow.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any

from apps.billing.models.time_entry import TimeEntry


ROUNDING_MODES = {"nearest": round, "up": math.ceil, "down": math.floor}


def round_time(duration_minutes: int, mode: str, increment_minutes: int) -> int:
    """Round duration per configured rules.

    Args:
        duration_minutes: Raw duration in minutes.
        mode: 'nearest', 'up', or 'down'.
        increment_minutes: Rounding increment (e.g. 15).

    Returns:
        Rounded duration in minutes.
    """
    if increment_minutes <= 0:
        return duration_minutes
    func = ROUNDING_MODES.get(mode, round)
    return int(func(duration_minutes / increment_minutes) * increment_minutes)


def calculate_duration(started_at: datetime, ended_at: datetime | None) -> int:
    """Calculate duration in minutes between two datetimes.

    Args:
        started_at: Start datetime.
        ended_at: End datetime (None returns 0).

    Returns:
        Duration in minutes.
    """
    if not ended_at:
        return 0
    return int((ended_at - started_at).total_seconds() / 60)


def calculate_billable_amount(rounded_minutes: int, rate: float) -> float:
    """Calculate billable amount from rounded time and hourly rate.

    Args:
        rounded_minutes: Rounded time in minutes.
        rate: Hourly billing rate.

    Returns:
        Billable amount.
    """
    return round((rounded_minutes / 60) * rate, 2)


def get_work_days(week_starting: date) -> list[date]:
    """Return Monday-Friday dates for a week.

    Args:
        week_starting: The Monday of the week.

    Returns:
        List of 5 weekday dates.
    """
    return [week_starting + timedelta(days=i) for i in range(5)]


def validate_timesheet(
    tenant_id: str, user_id: str, week_starting: date
) -> dict[str, Any]:
    """Validate a timesheet for the given user and week.

    Checks total hours, flags excessive entries, and identifies
    days with no logged time.

    Args:
        tenant_id: Tenant identifier.
        user_id: User identifier.
        week_starting: The Monday of the week.

    Returns:
        Dict with warnings, total_hours, and gap_days.
    """
    week_end = week_starting + timedelta(days=6)
    entries = TimeEntry.objects.filter(
        tenant_id=tenant_id,
        user_id=user_id,
        started_at__date__gte=week_starting,
        started_at__date__lte=week_end,
    )
    total_hours = sum(
        (e.duration_minutes for e in entries), start=0
    ) / 60.0
    warnings: list[str] = []
    if total_hours < 35:
        warnings.append(
            f"Timesheet has only {total_hours:.1f} hours. Expected 40+."
        )
    if total_hours > 60:
        warnings.append(
            f"Timesheet has {total_hours:.1f} hours. Please verify."
        )
    entry_dates = {e.started_at.date() for e in entries}
    gap_days = []
    for day in get_work_days(week_starting):
        if day not in entry_dates:
            warnings.append(f"No time logged for {day}")
            gap_days.append(str(day))
    return {
        "total_hours": round(total_hours, 2),
        "warnings": warnings,
        "gap_days": gap_days,
        "entry_count": entries.count(),
    }


def submit_timesheet(
    tenant_id: str, user_id: str, week_starting: date
) -> dict[str, Any]:
    """Submit a timesheet for approval.

    Updates all draft entries for the week to 'submitted' status
    and returns the validation result.

    Args:
        tenant_id: Tenant identifier.
        user_id: User identifier.
        week_starting: The Monday of the week.

    Returns:
        Dict with submission result.
    """
    week_end = week_starting + timedelta(days=6)
    validation = validate_timesheet(tenant_id, user_id, week_starting)
    updated = TimeEntry.objects.filter(
        tenant_id=tenant_id,
        user_id=user_id,
        started_at__date__gte=week_starting,
        started_at__date__lte=week_end,
        status=TimeEntry.Status.DRAFT,
    ).update(status=TimeEntry.Status.SUBMITTED, timesheet_week=week_starting)
    return {
        "submitted": True,
        "entries_updated": updated,
        "validation": validation,
        "week_starting": str(week_starting),
    }


def process_running_timers() -> int:
    """Process all running timers (ended_at is null).

    Called periodically by a background task. Computes current
    duration_minutes for entries where timer is still running.

    Returns:
        Number of running timers processed.
    """
    now = datetime.now()
    running = TimeEntry.objects.filter(
        tracking_mode=TimeEntry.TrackingMode.TIMER, ended_at__isnull=True
    )
    count = 0
    for entry in running:
        entry.duration_minutes = calculate_duration(entry.started_at, now)
        entry.save(update_fields=["duration_minutes", "updated_at"])
        count += 1
    return count
