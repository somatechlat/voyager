"""A/B Test schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class EmailABTestCreateSchema(Schema):
    """Schema for creating an A/B test."""

    tenant_id: str
    name: str
    test_type: str = "subject"
    campaign_name: str = ""
    sample_size: int | None = None
    sample_pct: Decimal = Decimal("20.00")
    confidence_level: Decimal = Decimal("0.950")
    winning_metric: str = "opens"
    auto_deploy: bool = True
    variants: list[dict[str, Any]] = []
    segment_id_ref: str = ""
    scheduled_at: datetime | None = None


class EmailABTestUpdateSchema(Schema):
    """Schema for updating an A/B test."""

    name: str | None = None
    test_type: str | None = None
    status: str | None = None
    sample_size: int | None = None
    sample_pct: Decimal | None = None
    confidence_level: Decimal | None = None
    winning_metric: str | None = None
    auto_deploy: bool | None = None
    variants: list[dict[str, Any]] | None = None
    results: dict[str, Any] | None = None
    scheduled_at: datetime | None = None


class EmailABTestListSchema(Schema):
    """Schema for A/B test list responses."""

    id: int
    tenant_id: str
    name: str
    test_type: str
    status: str
    sample_pct: Decimal
    confidence_level: Decimal
    winning_metric: str
    winner_variant_id: str
    auto_deploy: bool
    total_sent: int
    variant_count: int
    created_at: datetime


class EmailABTestDetailSchema(Schema):
    """Schema for detailed A/B test responses."""

    id: int
    tenant_id: str
    name: str
    test_type: str
    status: str
    campaign_name: str
    sample_size: int | None
    sample_pct: Decimal
    confidence_level: Decimal
    winning_metric: str
    winner_variant_id: str
    winner_selected_at: datetime | None
    auto_deploy: bool
    total_sent: int
    total_conversions: int
    variants: list[dict[str, Any]]
    results: dict[str, Any]
    segment_id_ref: str
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SampleSizeCalcSchema(Schema):
    """Schema for sample size calculation."""

    baseline_rate: float
    mde: float
    confidence: float = 0.95
    power: float = 0.80
    list_size: int | None = None


class WinnerSelectSchema(Schema):
    """Schema for winner selection."""

    variants: list[dict[str, Any]]
    metric: str = ""


class ABTestResultSchema(Schema):
    """Schema for chi-squared test input."""

    control_conversions: int
    control_total: int
    variant_conversions: int
    variant_total: int
