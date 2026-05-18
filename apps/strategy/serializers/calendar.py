"""Editorial Calendar serializers — SP-004 schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ninja import Schema


class CalendarEntryIn(Schema):
    """Input for creating/updating calendar entry."""

    title: str
    content_type: str
    platform: str = ""
    strategy_id: str | None = None
    campaign_id: str | None = None
    assignee_id: str | None = None
    due_date: date | None = None
    publish_date: date | None = None
    priority: int = 3
    estimated_hours: float | None = None
    notes: str = ""


class CalendarEntryOut(Schema):
    """Output for calendar entry."""

    id: str
    title: str
    content_type: str
    content_type_label: str
    color_code: str
    platform: str
    status: str
    status_label: str
    publish_date: date | None
    due_date: date | None
    assignee_id: str | None
    priority: int
    estimated_hours: float | None
    actual_hours: float | None
    notes: str
    created_at: datetime
    updated_at: datetime


class CalendarFilter(Schema):
    """Query filters for calendar view."""

    date_from: date | None = None
    date_to: date | None = None
    status: str | None = None
    assignee_id: str | None = None
    content_type: str | None = None
    campaign_id: str | None = None
    limit: int = 50
    offset: int = 0


class WorkloadOut(Schema):
    """Output for workload calculation."""

    workload: dict[str, dict[str, Any]]
    overloaded: list[dict[str, Any]]
    underloaded: list[dict[str, Any]]
    avg_utilization: float
    total_days: int
    overloaded_days: int
    underloaded_days: int


class StatusTransitionIn(Schema):
    """Input for pipeline status transition."""

    new_status: str


class PipelineSummaryOut(Schema):
    """Output for pipeline summary."""

    pipeline: dict[str, int]
    total_entries: int
    upcoming_deadlines: int
