"""Ninja schemas for Retainer endpoints."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class RetainerCreateSchema(Schema):
    """Schema for creating a retainer."""

    client_id: int
    name: str
    monthly_amount: Decimal
    monthly_hours: Decimal | None = None
    start_date: date
    end_date: date | None = None
    renewal_type: str = "auto"
    renewal_term_months: int = 12
    auto_invoice: bool = True
    invoice_day: int = 1
    rollover_policy: dict[str, Any] | None = None
    overage_rate: Decimal | None = None
    overage_billing_threshold: Decimal = Decimal("0")
    currency: str = "USD"
    consumption_alert_thresholds: list[int] | None = None
    notes: str = ""
    contract_url: str = ""
    metadata: dict[str, Any] | None = None


class RetainerUpdateSchema(Schema):
    """Schema for updating a retainer."""

    name: str | None = None
    monthly_amount: Decimal | None = None
    monthly_hours: Decimal | None = None
    end_date: date | None = None
    renewal_type: str | None = None
    auto_invoice: bool | None = None
    status: str | None = None
    overage_rate: Decimal | None = None
    notes: str | None = None


class RetainerListSchema(Schema):
    """Schema for listing retainers."""

    id: int
    client_id: int
    name: str
    monthly_amount: Decimal
    monthly_hours: Decimal | None
    start_date: date
    end_date: date | None
    status: str
    auto_invoice: bool
    currency: str
    created_at: datetime


class RetainerSchema(Schema):
    """Full schema for a retainer."""

    id: int
    tenant_id: str
    client_id: int
    name: str
    monthly_amount: Decimal
    monthly_hours: Decimal | None
    start_date: date
    end_date: date | None
    renewal_type: str
    renewal_term_months: int
    auto_invoice: bool
    invoice_day: int
    rollover_policy: dict[str, Any]
    overage_rate: Decimal | None
    overage_billing_threshold: Decimal
    status: str
    currency: str
    consumption_alert_thresholds: list[int]
    last_invoiced_month: date | None
    total_hours_consumed: Decimal
    total_amount_invoiced: Decimal
    notes: str
    contract_url: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RetainerConsumptionSchema(Schema):
    """Schema for retainer consumption."""

    hours_billed: Decimal
    hours_remaining: Decimal
    consumption_pct: Decimal
    month: str
    alerts: list[dict[str, Any]]


class RetainerRolloverSchema(Schema):
    """Schema for retainer rollover."""

    rollover_hours: Decimal
    forfeited_hours: Decimal
    overage_hours: Decimal
