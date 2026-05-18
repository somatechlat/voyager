"""Campaign management schemas (Django Ninja).

Request/response models for campaign CRUD, lifecycle, budget,
A/B testing, performance, and brief endpoints.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema
from ninja.orm import create_schema

# ---------------------------------------------------------------------------
# Campaign schemas
# ---------------------------------------------------------------------------


class CampaignCreateSchema(Schema):
    """Schema for creating a campaign."""

    name: str
    description: str = ""
    objective: str = "awareness"
    client_id: int
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = None
    currency: str = "USD"
    pacing_type: str = "even"
    attribution_model: str = "last_touch"
    channels: list[str] = []
    target_audience: dict[str, Any] = {}
    kpis: dict[str, Any] = {}


class CampaignUpdateSchema(Schema):
    """Schema for updating a campaign."""

    name: str | None = None
    description: str | None = None
    objective: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = None
    currency: str | None = None
    pacing_type: str | None = None
    attribution_model: str | None = None
    channels: list[str] | None = None
    target_audience: dict[str, Any] | None = None
    kpis: dict[str, Any] | None = None
    status: str | None = None


class CampaignListSchema(Schema):
    """Schema for campaign list responses."""

    id: int
    tenant_id: str
    name: str
    objective: str
    stage: str
    status: str
    start_date: date | None
    end_date: date | None
    budget: Decimal | None
    current_spend: Decimal
    currency: str
    pacing_type: str
    client_id: int
    created_by: str
    created_at: datetime
    updated_at: datetime


class CampaignDetailSchema(Schema):
    """Schema for detailed campaign responses."""

    id: int
    tenant_id: str
    name: str
    description: str
    objective: str
    stage: str
    status: str
    start_date: date | None
    end_date: date | None
    budget: Decimal | None
    current_spend: Decimal
    currency: str
    pacing_type: str
    attribution_model: str
    channels: list[str]
    target_audience: dict[str, Any]
    kpis: dict[str, Any]
    brief_approved: bool
    all_creatives_approved: bool
    approval_status: str
    all_platforms_published: bool
    client_id: int
    created_by: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Lifecycle schemas
# ---------------------------------------------------------------------------


class StageTransitionSchema(Schema):
    """Schema for stage transition request."""

    target_stage: str


class StageTransitionResponseSchema(Schema):
    """Schema for stage transition response."""

    success: bool
    previous_stage: str
    new_stage: str
    errors: list[str]


class AvailableStageSchema(Schema):
    """Schema for available stage info."""

    stage: str
    label: str
    valid: bool
    errors: list[str]


# ---------------------------------------------------------------------------
# Channel schemas
# ---------------------------------------------------------------------------


class ChannelCreateSchema(Schema):
    """Schema for creating a campaign channel."""

    channel_type: str
    platform: str
    config: dict[str, Any] = {}
    daily_budget: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    dependencies: list[str] = []
    lead_time_days: int = 0


class ChannelUpdateSchema(Schema):
    """Schema for updating a campaign channel."""

    platform: str | None = None
    config: dict[str, Any] | None = None
    daily_budget: Decimal | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    dependencies: list[str] | None = None
    lead_time_days: int | None = None


class ChannelListSchema(Schema):
    """Schema for channel list responses."""

    id: int
    channel_type: str
    platform: str
    status: str
    daily_budget: Decimal | None
    total_spend: Decimal
    start_date: date | None
    end_date: date | None
    lead_time_days: int
    created_at: datetime


class ChannelScheduleSchema(Schema):
    """Schema for channel scheduling response."""

    channel_id: int
    channel_type: str
    platform: str
    scheduled_start: str
    scheduled_end: str
    lead_time_days: int
    depends_on: list[int]


# ---------------------------------------------------------------------------
# A/B Test schemas
# ---------------------------------------------------------------------------


class ABTestCreateSchema(Schema):
    """Schema for creating an A/B test."""

    name: str
    test_type: str
    method: str = "frequentist"
    significance_level: Decimal = Decimal("0.05")
    power: Decimal = Decimal("0.80")
    baseline_rate: Decimal | None = None
    minimum_detectable_effect: Decimal | None = None
    daily_traffic: int | None = None
    winner_criteria: str = "conversion_rate"
    variants: list[dict[str, Any]] = []


class ABTestUpdateSchema(Schema):
    """Schema for updating an A/B test."""

    name: str | None = None
    status: str | None = None
    variants: list[dict[str, Any]] | None = None


class ABTestListSchema(Schema):
    """Schema for A/B test list."""

    id: int
    name: str
    test_type: str
    method: str
    status: str
    winner_criteria: str
    sample_size_per_variant: int | None
    estimated_duration_days: int | None
    created_at: datetime


class ABTestResultSchema(Schema):
    """Schema for A/B test results."""

    winner: dict[str, Any] | None
    results: list[dict[str, Any]]
    method: str


# ---------------------------------------------------------------------------
# Budget schemas
# ---------------------------------------------------------------------------


class BudgetSpendSchema(Schema):
    """Schema for recording spend."""

    amount: Decimal
    channel: str = ""
    description: str = ""
    metadata: dict[str, Any] = {}


class BudgetAllocationSchema(Schema):
    """Schema for recording allocation."""

    amount: Decimal
    description: str = ""


class PacingResultSchema(Schema):
    """Schema for pacing calculation result."""

    daily_budget: float
    pacing_type: str
    days_remaining: int
    reasoning: str = ""
    channel_breakdown: list[dict[str, Any]] = []


class BudgetAlertSchema(Schema):
    """Schema for budget alerts."""

    level: str | int
    message: str
    severity: str


# ---------------------------------------------------------------------------
# Performance schemas
# ---------------------------------------------------------------------------


class PerformanceRecordSchema(Schema):
    """Schema for recording daily performance."""

    metric_date: date
    channel_id: int | None = None
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: Decimal = Decimal("0")
    revenue: Decimal = Decimal("0")
    engagement_actions: int = 0
    metrics: dict[str, Any] = {}


class DashboardKPIsSchema(Schema):
    """Schema for dashboard KPI response."""

    campaign: dict[str, Any]
    kpis: dict[str, Any]
    sparkline: dict[str, list[Any]]
    channel_breakdown: list[dict[str, Any]]


class ROISchema(Schema):
    """Schema for ROI calculation."""

    labor_cost: float = 0.0
    tool_costs: float = 0.0
    overhead_pct: float = 0.15


# ---------------------------------------------------------------------------
# Brief schemas
# ---------------------------------------------------------------------------


class BriefApproveSchema(Schema):
    """Schema for approving a brief."""

    approved: bool = True


class BriefResponseSchema(Schema):
    """Schema for brief response."""

    id: int
    version: int
    objective_type: str
    estimated_timeline_days: int | None
    suggested_budget: dict[str, Any]
    is_approved: bool
    created_at: datetime
