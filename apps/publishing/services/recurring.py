"""Recurring service — cron parsing and recurring post instance generation.

Parses cron expressions and generates ScheduledPost instances from
RecurringPost definitions, handling content variation strategies.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone

from ..models import RecurringPost, ScheduledPost

logger = logging.getLogger(__name__)


class CronParser:
    """Parse cron expressions into datetime occurrences."""

    @staticmethod
    def parse(cron_expr: str) -> dict[str, list[int]]:
        """Parse a cron expression into field values.

        Args:
            cron_expr: Standard 5-field cron: "min hour day month dow".

        Returns:
            Dict with minute, hour, day, month, dow as int lists.
        """
        parts = cron_expr.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron_expr}")

        return {
            "minute": CronParser._parse_field(parts[0], 0, 59),
            "hour": CronParser._parse_field(parts[1], 0, 23),
            "day": CronParser._parse_field(parts[2], 1, 31),
            "month": CronParser._parse_field(parts[3], 1, 12),
            "dow": CronParser._parse_field(parts[4], 0, 7),
        }

    @staticmethod
    def _parse_field(field: str, min_val: int, max_val: int) -> list[int]:
        """Parse a single cron field.

        Supports: *, ranges (1-5), steps (*/2), lists (1,3,5).
        """
        values: set[int] = set()

        # Handle dow=7 as 0 (Sunday)
        effective_max = max_val
        if field == "*":
            return list(range(min_val, effective_max + 1))

        for part in field.split(","):
            # Step: */N
            if part.startswith("*/"):
                step = int(part[2:])
                values.update(range(min_val, effective_max + 1, step))
                continue
            # Step with range: 1-5/2
            if "/" in part:
                range_part, step_str = part.split("/", 1)
                step = int(step_str)
                if "-" in range_part:
                    start, end = range_part.split("-", 1)
                    values.update(range(int(start), int(end) + 1, step))
                elif range_part == "*":
                    values.update(range(min_val, effective_max + 1, step))
                continue
            # Range: 1-5
            if "-" in part:
                start, end = part.split("-", 1)
                values.update(range(int(start), int(end) + 1))
                continue
            # Single value
            try:
                val = int(part)
                # Normalize dow
                if max_val == 7 and val == 7:
                    val = 0
                values.add(val)
            except ValueError:
                continue

        return sorted(v for v in values if min_val <= v <= effective_max)

    @staticmethod
    def get_next_occurrences(
        cron_expr: str,
        start: datetime,
        end: datetime,
        max_count: int = 100,
    ) -> list[datetime]:
        """Get next occurrences of a cron expression within a date range.

        Args:
            cron_expr: Cron expression.
            start: Start datetime.
            end: End datetime.
            max_count: Maximum occurrences to return.

        Returns:
            List of occurrence datetimes.
        """
        parsed = CronParser.parse(cron_expr)
        occurrences: list[datetime] = []

        current = start.replace(minute=0, second=0, microsecond=0)
        # Walk day by day
        day_ptr = current.date()
        end_date = end.date()
        safety = 0

        while day_ptr <= end_date and len(occurrences) < max_count and safety < 500:
            safety += 1
            weekday = day_ptr.weekday()
            # Check dow (0=Mon, 6=Sun; cron uses 0/7=Sun)
            cron_dow = weekday + 1
            if cron_dow == 7:
                cron_dow = 0
            if cron_dow not in parsed["dow"]:
                day_ptr += timedelta(days=1)
                continue
            # Check month
            if day_ptr.month not in parsed["month"]:
                day_ptr += timedelta(days=1)
                continue
            # Check day of month
            if day_ptr.day not in parsed["day"]:
                day_ptr += timedelta(days=1)
                continue

            # Generate times for this day
            for hour in sorted(parsed["hour"]):
                for minute in sorted(parsed["minute"]):
                    dt = datetime.combine(
                        day_ptr, datetime.min.time().replace(hour=hour, minute=minute),
                    )
                    if start.tzinfo:
                        dt = dt.replace(tzinfo=start.tzinfo)
                    if start <= dt <= end:
                        occurrences.append(dt)
                    if len(occurrences) >= max_count:
                        break
                if len(occurrences) >= max_count:
                    break

            day_ptr += timedelta(days=1)

        return sorted(occurrences)


# Predefined patterns
PREDEFINED_PATTERNS: dict[str, str] = {
    "daily": "0 9 * * *",
    "weekdays": "0 9 * * 1-5",
    "weekly": "0 9 * * 1",
    "biweekly": "0 9 */14 * 1",
    "monthly": "0 9 1 * *",
}


def generate_recurring_instances(
    series: RecurringPost,
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Generate scheduled post instances from a recurring series.

    Args:
        series: The RecurringPost definition.
        start: Override start date.
        end: Override end date.

    Returns:
        List of instance dicts with scheduled_at, content, etc.
    """
    from ..models import PublishQueue

    if not start:
        start = timezone.now()
    if not end:
        end = start + timedelta(days=30)

    cron = series.cron_expression
    if cron in PREDEFINED_PATTERNS:
        cron = PREDEFINED_PATTERNS[cron]

    try:
        occurrences = CronParser.get_next_occurrences(cron, start, end, max_count=100)
    except ValueError as exc:
        logger.error("Invalid cron for series %s: %s", series.id, exc)
        return []

    if series.end_date and end > series.end_date:
        end = series.end_date

    instances: list[dict[str, Any]] = []
    instance_number = series.last_instance_number

    for occ in occurrences:
        if series.end_date and occ > series.end_date:
            break

        instance_number += 1
        content = series.select_content_variant(instance_number)

        instances.append({
            "scheduled_at": occ,
            "content": content,
            "series_id": str(series.id),
            "instance_number": instance_number,
            "platform": series.platform,
            "account_id": str(series.account_id),
            "publish_type": series.publish_type,
        })

    return instances


def create_scheduled_posts_from_instances(
    series: RecurringPost,
    instances: list[dict[str, Any]],
    created_by: str,
) -> list[ScheduledPost]:
    """Create ScheduledPost records from generated instances.

    Args:
        series: The RecurringPost definition.
        instances: Generated instance dicts.
        created_by: User UUID.

    Returns:
        List of created ScheduledPost instances.
    """
    from ..models import PublishQueue

    created: list[ScheduledPost] = []

    for inst in instances:
        content = inst["content"]
        post = ScheduledPost.objects.create(
            tenant_id=series.tenant_id,
            platform=inst["platform"],
            account_id=inst["account_id"],
            publish_type=inst["publish_type"],
            caption=content.get("caption", ""),
            hashtags=content.get("hashtags", []),
            media_urls=content.get("media_urls", []),
            link=content.get("link", ""),
            alt_text=content.get("alt_text", ""),
            scheduled_at=inst["scheduled_at"],
            timezone=series.timezone,
            status=ScheduledPost.Status.SCHEDULED,
            priority=ScheduledPost.Priority.LOW,
            created_by=created_by,
            tags=series.context_json.get("tags", []),
        )
        # Create calendar entry
        from ..models import ContentCalendar
        ContentCalendar.objects.create(
            tenant_id=series.tenant_id,
            scheduled_post=post,
            calendar_view=ContentCalendar.CalendarView.MONTH,
        )
        # Queue
        PublishQueue.objects.get_or_create(
            scheduled_post=post,
            defaults={"queue_priority": 3},
        )
        created.append(post)

    # Update series tracking
    if instances:
        last = instances[-1]
        series.last_instance_at = last["scheduled_at"]
        series.last_instance_number = last["instance_number"]
        series.save(update_fields=["last_instance_at", "last_instance_number"])

    logger.info(
        "Created %d scheduled posts from series %s",
        len(created), series.id,
    )
    return created


def process_all_recurring(
    tenant_id: str | None = None,
) -> dict[str, int]:
    """Process all active recurring post definitions.

    Args:
        tenant_id: Optional tenant filter.

    Returns:
        Dict with created count.
    """
    qs = RecurringPost.objects.filter(is_active=True)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    total_created = 0
    for series in qs:
        try:
            instances = generate_recurring_instances(series)
            if instances:
                created = create_scheduled_posts_from_instances(
                    series, instances, series.created_by,
                )
                total_created += len(created)
        except Exception:
            logger.exception("Error processing recurring series %s", series.id)

    return {"created": total_created}
