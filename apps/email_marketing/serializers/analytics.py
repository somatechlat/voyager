"""Analytics schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class EmailAnalyticsListSchema(Schema):
    """Schema for analytics list responses."""

    id: int
    tenant_id: str
    campaign_id: int
    sent: int
    delivered: int
    unique_opens: int
    unique_clicks: int
    open_rate: float
    click_rate: float
    calculated_at: datetime | None
    created_at: datetime


class EmailAnalyticsDetailSchema(Schema):
    """Schema for detailed analytics responses."""

    id: int
    tenant_id: str
    campaign_id: int
    sent: int
    delivered: int
    opens: int
    unique_opens: int
    clicks: int
    unique_clicks: int
    bounces: int
    hard_bounces: int
    soft_bounces: int
    spam_complaints: int
    unsubscribes: int
    revenue: Decimal
    conversions: int
    open_rate: float
    click_rate: float
    ctr: float
    bounce_rate: float
    conversion_rate: float
    revenue_per_email: float
    calculated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class HeatmapGenerateSchema(Schema):
    """Schema for heatmap generation."""

    blocks: list[dict[str, Any]]
    click_events: list[dict[str, Any]]
    total_delivered: int = 0


class EngagementTierSchema(Schema):
    """Schema for engagement tier computation."""

    tenant_id: str


class DeviceBreakdownSchema(Schema):
    """Schema for device breakdown."""

    tenant_id: str
    device_data: list[dict[str, Any]] | None = None


class HourlyBreakdownSchema(Schema):
    """Schema for hourly breakdown."""

    events: list[dict[str, Any]]
