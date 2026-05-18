"""Ninja schemas for Time Entry endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema

from apps.billing.serializers.base import TaxRateSchema  # noqa: F401


class TimeEntryCreateSchema(Schema):
    """Schema for creating a time entry."""

    user_id: str
    client_id: int
    project_id: int | None = None
    task_name: str = ""
    description: str = ""
    tracking_mode: str = "manual"
    started_at: datetime
    ended_at: datetime | None = None
    billing_rate: Decimal | None = None
    is_billable: bool = True
    rounding_mode: str = "nearest"
    rounding_increment: int = 15
    source_data: dict[str, Any] | None = None


class TimeEntryUpdateSchema(Schema):
    """Schema for updating a time entry."""

    task_name: str | None = None
    description: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    billing_rate: Decimal | None = None
    is_billable: bool | None = None
    status: str | None = None
    timesheet_week: date | None = None


class TimeEntryListSchema(Schema):
    """Schema for listing time entries."""

    id: int
    user_id: str
    client_id: int
    project_id: int | None
    task_name: str
    tracking_mode: str
    started_at: datetime
    ended_at: datetime | None
    duration_minutes: int
    rounded_minutes: int
    billing_rate: Decimal | None
    billable_amount: Decimal | None
    is_billable: bool
    status: str


class TimeEntrySchema(Schema):
    """Full schema for a time entry."""

    id: int
    tenant_id: str
    user_id: str
    client_id: int
    project_id: int | None
    task_name: str
    description: str
    tracking_mode: str
    started_at: datetime
    ended_at: datetime | None
    duration_minutes: int
    rounded_minutes: int
    rounding_mode: str
    rounding_increment: int
    billing_rate: Decimal | None
    billable_amount: Decimal | None
    is_billable: bool
    status: str
    timesheet_week: date | None
    approver_id: str
    approved_at: datetime | None
    rejection_reason: str
    source_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class TimesheetSubmitSchema(Schema):
    """Schema for submitting a timesheet."""

    user_id: str
    week_starting: date


class TimesheetValidationSchema(Schema):
    """Schema for timesheet validation results."""

    total_hours: float
    warnings: list[str]
    gap_days: list[str]
    entry_count: int
