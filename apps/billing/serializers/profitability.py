"""Ninja schemas for Profitability endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class ProfitabilityListSchema(Schema):
    """Schema for listing profitability reports."""

    id: int
    tenant_id: str
    dimension: str
    dimension_id: str
    dimension_name: str
    period_start: date
    period_end: date
    revenue: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    gross_margin_pct: Decimal
    is_current: bool
    created_at: datetime


class ProfitabilitySchema(Schema):
    """Full schema for a profitability report."""

    id: int
    tenant_id: str
    dimension: str
    dimension_id: str
    dimension_name: str
    period_start: date
    period_end: date
    revenue: Decimal
    labor_cost: Decimal
    tool_cost: Decimal
    expense_cost: Decimal
    overhead_cost: Decimal
    total_cost: Decimal
    gross_profit: Decimal
    gross_margin_pct: Decimal
    benchmark_margin_pct: Decimal | None
    margin_vs_benchmark: Decimal | None
    breakdown: dict[str, Any]
    trend_data: dict[str, Any]
    hours_billed: Decimal
    hours_logged: Decimal
    effective_hourly_rate: Decimal | None
    status: str
    is_current: bool
    created_at: datetime
    updated_at: datetime


class ProfitabilitySummarySchema(Schema):
    """Schema for profitability summary."""

    total_revenue: str
    total_cost: str
    total_profit: str
    avg_margin_pct: str
    report_count: int
