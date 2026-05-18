"""Ninja schemas for Budget endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class BudgetCreateSchema(Schema):
    """Schema for creating a project budget."""

    project_id: int
    budget_type: str = "fixed"
    total_budget: Decimal
    hours_allocated: Decimal | None = None
    hourly_rate: Decimal | None = None
    monthly_retainer: Decimal | None = None
    base_retainer: Decimal | None = None
    overage_rate: Decimal | None = None
    start_date: date
    end_date: date | None = None
    currency: str = "USD"


class BudgetUpdateSchema(Schema):
    """Schema for updating a project budget."""

    total_budget: Decimal | None = None
    hours_allocated: Decimal | None = None
    hourly_rate: Decimal | None = None
    monthly_retainer: Decimal | None = None
    base_retainer: Decimal | None = None
    overage_rate: Decimal | None = None
    end_date: date | None = None
    alert_thresholds: dict[str, Any] | None = None


class BudgetListSchema(Schema):
    """Schema for listing budgets."""

    id: int
    project_id: int
    budget_type: str
    total_budget: Decimal
    budget_consumed: Decimal
    alert_level: str
    start_date: date
    end_date: date | None
    currency: str
    created_at: datetime


class BudgetSchema(Schema):
    """Full schema for a project budget."""

    id: int
    tenant_id: str
    project_id: int
    budget_type: str
    total_budget: Decimal
    hours_allocated: Decimal | None
    hourly_rate: Decimal | None
    monthly_retainer: Decimal | None
    base_retainer: Decimal | None
    overage_rate: Decimal | None
    budget_consumed: Decimal
    hours_consumed: Decimal
    alert_level: str
    alert_thresholds: dict[str, Any]
    forecast_data: dict[str, Any]
    start_date: date
    end_date: date | None
    currency: str
    created_at: datetime
    updated_at: datetime


class BudgetConsumptionSchema(Schema):
    """Schema for budget consumption result."""

    budget_consumed: str
    hours_consumed: str
    alert: dict[str, Any]


class BudgetForecastSchema(Schema):
    """Schema for budget forecast."""

    budget_total: str
    budget_consumed: str
    budget_remaining: str
    consumption_pct: float
    daily_burn_rate: float
    estimated_completion_date: str
    days_over_under: int
    on_budget: bool
    projected_overrun: float
