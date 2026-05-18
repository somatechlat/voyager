"""ContentCalendar model — stores calendar entries and blackout windows.

Tracks calendar entries for drag-and-drop scheduling and blackout
windows for conflict detection across platforms.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone as tz

from apps.core.models import UUIDModel, TimeStampedModel, TenantModel


class ContentCalendar(UUIDModel, TimeStampedModel, TenantModel):
    """A calendar view entry for a scheduled post.

    Used for drag-and-drop calendar rendering and conflict detection.
    Links to a ScheduledPost and stores position/colour metadata.

    Attributes:
        scheduled_post: FK to the scheduled post.
        calendar_view: Which calendar view (day, week, month, quarter).
        position_order: Order for rendering within a calendar cell.
        color_override: Optional hex colour override.
    """

    class CalendarView(models.TextChoices):
        DAY = "day", "Day"
        WEEK = "week", "Week"
        MONTH = "month", "Month"
        QUARTER = "quarter", "Quarter"

    scheduled_post = models.OneToOneField(
        "ScheduledPost",
        on_delete=models.CASCADE,
        related_name="calendar_entry",
    )
    calendar_view = models.CharField(
        max_length=16,
        choices=CalendarView.choices,
        default=CalendarView.MONTH,
    )
    position_order = models.PositiveIntegerField(
        default=0,
        help_text="Render order within a calendar cell",
    )
    color_override = models.CharField(
        max_length=7,
        blank=True,
        help_text="Optional hex colour override (#RRGGBB)",
    )

    class Meta:
        db_table = "voyager_content_calendar"
        verbose_name = "Content Calendar Entry"
        verbose_name_plural = "Content Calendar Entries"
        ordering = ["scheduled_post__scheduled_at"]
        indexes = [
            models.Index(fields=["tenant_id", "calendar_view"]),
        ]

    def __str__(self) -> str:
        return f"Calendar {self.calendar_view} — {self.scheduled_post_id}"

    @classmethod
    def get_conflicts(
        cls,
        tenant_id: str,
        platform: str,
        account_id: str,
        scheduled_at: datetime,
        window_minutes: int = 30,
        exclude_id: str | None = None,
    ) -> models.QuerySet:
        """Find posts conflicting within a time window.

        Args:
            tenant_id: Tenant scope.
            platform: Platform to check.
            account_id: Account to check.
            scheduled_at: Target scheduled time.
            window_minutes: +/- minutes to consider conflict.
            exclude_id: Optional post ID to exclude (for rescheduling).

        Returns:
            QuerySet of conflicting ContentCalendar entries.
        """
        start = scheduled_at - timedelta(minutes=window_minutes)
        end = scheduled_at + timedelta(minutes=window_minutes)

        qs = cls.objects.filter(
            tenant_id=tenant_id,
            scheduled_post__platform=platform,
            scheduled_post__account_id=account_id,
            scheduled_post__scheduled_at__gte=start,
            scheduled_post__scheduled_at__lte=end,
        ).exclude(
            scheduled_post__status="cancelled",
        )
        if exclude_id:
            qs = qs.exclude(scheduled_post_id=exclude_id)
        return qs.select_related("scheduled_post")


class BlackoutWindow(UUIDModel, TimeStampedModel, TenantModel):
    """A blackout period during which no posts can be scheduled.

    Attributes:
        name: Human-readable name for the blackout.
        account_id: Optional account scope (null = all accounts).
        platform: Optional platform scope (blank = all platforms).
        start_at: Blackout start time.
        end_at: Blackout end time.
        recurring: Whether this repeats (daily, weekly, monthly).
    """

    class RecurringType(models.TextChoices):
        NONE = "none", "Does not repeat"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    name = models.CharField(max_length=255, help_text="Blackout name")
    account_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Account scope; null = all accounts",
    )
    platform = models.CharField(
        max_length=32,
        blank=True,
        db_index=True,
        help_text="Platform scope; blank = all platforms",
    )
    start_at = models.DateTimeField(help_text="Blackout start")
    end_at = models.DateTimeField(help_text="Blackout end")
    recurring = models.CharField(
        max_length=16,
        choices=RecurringType.choices,
        default=RecurringType.NONE,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    metadata_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional blackout metadata",
    )

    class Meta:
        db_table = "voyager_blackout_window"
        verbose_name = "Blackout Window"
        verbose_name_plural = "Blackout Windows"
        ordering = ["-start_at"]
        indexes = [
            models.Index(fields=["tenant_id", "account_id", "platform"]),
            models.Index(fields=["tenant_id", "start_at", "end_at"]),
            models.Index(fields=["is_active", "start_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_at} → {self.end_at})"

    def is_blackout(self, dt: datetime) -> bool:
        """Check if datetime falls within this blackout window."""
        if not self.is_active:
            return False
        if self.recurring == self.RecurringType.NONE:
            return self.start_at <= dt <= self.end_at
        # For recurring, compare time components
        start_time = self.start_at.time()
        end_time = self.end_at.time()
        dt_time = dt.astimezone(tz.utc).time() if dt.tzinfo else dt.time()
        if self.recurring == self.RecurringType.DAILY:
            return start_time <= dt_time <= end_time
        if self.recurring == self.RecurringType.WEEKLY:
            start_dow = self.start_at.weekday()
            if dt.weekday() != start_dow:
                return False
            return start_time <= dt_time <= end_time
        if self.recurring == self.RecurringType.MONTHLY:
            start_day = self.start_at.day
            if dt.day != start_day:
                return False
            return start_time <= dt_time <= end_time
        return False
