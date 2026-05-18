"""Scheduler service — finds optimal time slots for publishing.

Based on historical engagement data, timezone distribution, and
platform algorithm patterns to maximize content reach.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)

# Platform default frequency limits
PLATFORM_DEFAULTS: dict[str, dict[str, int]] = {
    "instagram": {"maxPerDay": 3, "maxPerWeek": 14, "minInterval": 120},
    "linkedin": {"maxPerDay": 2, "maxPerWeek": 10, "minInterval": 180},
    "twitter": {"maxPerDay": 7, "maxPerWeek": 49, "minInterval": 30},
    "tiktok": {"maxPerDay": 3, "maxPerWeek": 14, "minInterval": 120},
    "facebook": {"maxPerDay": 3, "maxPerWeek": 14, "minInterval": 120},
    "youtube": {"maxPerDay": 1, "maxPerWeek": 4, "minInterval": 1440},
    "pinterest": {"maxPerDay": 10, "maxPerWeek": 50, "minInterval": 30},
    "threads": {"maxPerDay": 3, "maxPerWeek": 14, "minInterval": 120},
}

# Default engagement weights per hour (0-23 UTC)
DEFAULT_HOURLY_WEIGHTS: dict[int, float] = {
    0: 0.3,
    1: 0.2,
    2: 0.1,
    3: 0.1,
    4: 0.1,
    5: 0.2,
    6: 0.4,
    7: 0.6,
    8: 0.8,
    9: 0.9,
    10: 0.85,
    11: 0.8,
    12: 0.75,
    13: 0.8,
    14: 0.85,
    15: 0.9,
    16: 0.85,
    17: 0.8,
    18: 0.7,
    19: 0.75,
    20: 0.8,
    21: 0.7,
    22: 0.5,
    23: 0.4,
}

# Day-of-week weights (0=Monday)
DOW_WEIGHTS: dict[int, float] = {
    0: 0.9,
    1: 0.95,
    2: 1.0,
    3: 0.95,
    4: 0.9,
    5: 0.6,
    6: 0.5,
}


def get_frequency_limits(
    account_id: str,
    platform: str,
) -> dict[str, int | list[dict[str, Any]]]:
    """Calculate frequency limits for an account/platform.

    Args:
        account_id: Platform account UUID.
        platform: Platform name.

    Returns:
        Dict with maxPerDay, maxPerWeek, minIntervalMinutes, blackoutWindows.
    """
    defaults = PLATFORM_DEFAULTS.get(
        platform, {"maxPerDay": 3, "maxPerWeek": 14, "minInterval": 120}
    )
    return {
        "maxPerDay": defaults["maxPerDay"],
        "maxPerWeek": defaults["maxPerWeek"],
        "minIntervalMinutes": defaults["minInterval"],
        "blackoutWindows": [],
    }


def get_daily_post_count(
    tenant_id: str,
    platform: str,
    account_id: str,
    date: datetime,
) -> int:
    """Count posts already scheduled for a given date.

    Args:
        tenant_id: Tenant scope.
        platform: Platform name.
        account_id: Account UUID.
        date: Date to check.

    Returns:
        Number of scheduled/published posts for that date.
    """
    from ..models import ScheduledPost

    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return ScheduledPost.objects.filter(
        tenant_id=tenant_id,
        platform=platform,
        account_id=account_id,
        scheduled_at__gte=start,
        scheduled_at__lt=end,
        status__in=[
            ScheduledPost.Status.SCHEDULED,
            ScheduledPost.Status.PUBLISHING,
            ScheduledPost.Status.PUBLISHED,
        ],
    ).count()


def is_within_frequency_limit(
    tenant_id: str,
    platform: str,
    account_id: str,
    scheduled_at: datetime,
) -> bool:
    """Check if scheduling respects frequency limits.

    Args:
        tenant_id: Tenant scope.
        platform: Platform name.
        account_id: Account UUID.
        scheduled_at: Proposed scheduled time.

    Returns:
        True if within limits.
    """
    limits = get_frequency_limits(account_id, platform)
    daily = get_daily_post_count(tenant_id, platform, account_id, scheduled_at)
    return daily < limits["maxPerDay"]  # type: ignore[operator]


def score_time_slot(
    dt: datetime,
    platform: str,
    account_id: str,
    engagement_data: dict[str, list[float]] | None = None,
) -> float:
    """Score a time slot for optimal publishing.

    Args:
        dt: The time slot to score.
        platform: Target platform.
        account_id: Account UUID.
        engagement_data: Optional engagement data dict keyed by "dow_hour".

    Returns:
        Score (higher = better).
    """
    hour = dt.hour
    dow = dt.weekday()

    # Base score from hourly/dow weights
    base = DEFAULT_HOURLY_WEIGHTS.get(hour, 0.5)
    dow_mult = DOW_WEIGHTS.get(dow, 1.0)
    score = base * dow_mult

    # Override with real engagement data if available
    if engagement_data:
        key = f"{dow}_{hour}"
        values = engagement_data.get(key, [])
        if values:
            mean_val = sum(values) / len(values)
            sorted_vals = sorted(values)
            mid = len(sorted_vals) // 2
            median_val = (
                sorted_vals[mid]
                if len(sorted_vals) % 2
                else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
            )
            score = mean_val * 0.7 + median_val * 0.3

    # Apply penalties
    if engagement_data and "blackout" in engagement_data:
        blackout = engagement_data["blackout"]
        for bw in blackout:
            if bw["start"] <= dt <= bw["end"]:
                score = 0
                break

    return round(score, 4)


def find_optimal_slot(
    tenant_id: str,
    platform: str,
    account_id: str,
    preferred_date: datetime,
    engagement_data: dict[str, list[float]] | None = None,
    num_slots: int = 5,
) -> dict[str, Any]:
    """Find optimal time slots for publishing.

    Args:
        tenant_id: Tenant scope.
        platform: Target platform.
        account_id: Account UUID.
        preferred_date: Preferred date to publish.
        engagement_data: Optional engagement data.
        num_slots: How many slots to return.

    Returns:
        Dict with best_slot and scored_slots list.
    """
    slots: list[dict[str, Any]] = []
    limits = get_frequency_limits(account_id, platform)
    min_interval = limits["minIntervalMinutes"]  # type: ignore[operator]

    # Generate slots from 6am to 10pm, every min_interval minutes
    day_start = preferred_date.replace(hour=6, minute=0, second=0, microsecond=0)
    for hour_offset in range(0, 16 * 60, min_interval):  # type: ignore[operator]
        slot_time = day_start + timedelta(minutes=hour_offset)
        score = score_time_slot(slot_time, platform, account_id, engagement_data)
        slots.append(
            {
                "datetime": slot_time,
                "score": score,
                "day_of_week": slot_time.weekday(),
                "hour": slot_time.hour,
            }
        )

    # Check frequency limits and penalize conflicts
    for slot in slots:
        within_limit = is_within_frequency_limit(
            tenant_id,
            platform,
            account_id,
            slot["datetime"],
        )
        if not within_limit:
            slot["score"] = 0.0
            slot["reason"] = "frequency_limit"

    # Sort by score descending
    slots.sort(key=lambda s: s["score"], reverse=True)

    best = slots[0] if slots else None
    return {
        "best_slot": best,
        "scored_slots": slots[:num_slots],
        "platform": platform,
    }


def calculate_timezone_spread(
    timezone_distribution: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Calculate 'golden hours' across audience timezones.

    Args:
        timezone_distribution: List of {"name": tz, "percentage": pct}.

    Returns:
        List of golden hours sorted by reach percentage.
    """
    golden_hours: list[dict[str, Any]] = []
    for utc_hour in range(24):
        awake_pct = 0.0
        for tz_entry in timezone_distribution:
            tz_name = tz_entry.get("name", "UTC")
            pct = tz_entry.get("percentage", 0)
            # Convert UTC hour to local hour
            try:
                import pytz

                tz = pytz.timezone(tz_name)
                dt = datetime.now(UTC).replace(hour=utc_hour, minute=0, second=0)
                local_dt = dt.astimezone(tz)
                local_hour = local_dt.hour
                if 8 <= local_hour <= 22:
                    awake_pct += pct
            except Exception:
                # Fallback: assume UTC
                if 8 <= utc_hour <= 22:
                    awake_pct += pct
        if awake_pct > 60:
            golden_hours.append({"hour": utc_hour, "reach": round(awake_pct, 2)})

    golden_hours.sort(key=lambda h: h["reach"], reverse=True)
    return golden_hours


def get_next_available_slot(
    tenant_id: str,
    platform: str,
    account_id: str,
    from_time: datetime | None = None,
) -> datetime | None:
    """Find the next available slot respecting all constraints.

    Args:
        tenant_id: Tenant scope.
        platform: Target platform.
        account_id: Account UUID.
        from_time: Start searching from this time.

    Returns:
        Next available datetime or None.
    """
    if from_time is None:
        from_time = timezone.now()

    # Search up to 14 days ahead
    for day_offset in range(14):
        candidate = from_time + timedelta(days=day_offset)
        candidate = candidate.replace(hour=9, minute=0, second=0, microsecond=0)
        if is_within_frequency_limit(tenant_id, platform, account_id, candidate):
            return candidate

    return None
