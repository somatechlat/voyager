"""Deliverability schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class DeliverabilityCreateSchema(Schema):
    """Schema for creating a deliverability monitor."""

    tenant_id: str
    domain: str


class DeliverabilityUpdateSchema(Schema):
    """Schema for updating a deliverability monitor."""

    domain: str | None = None
    reputation_score: Decimal | None = None
    reputation_grade: str | None = None
    bounce_rate: Decimal | None = None
    spam_complaint_rate: Decimal | None = None
    blacklist_status: dict[str, Any] | None = None
    recommendations: list[str] | None = None


class DeliverabilityListSchema(Schema):
    """Schema for deliverability list responses."""

    id: int
    tenant_id: str
    domain: str
    reputation_score: Decimal
    reputation_grade: str
    bounce_rate: Decimal
    spam_complaint_rate: Decimal
    checked_at: datetime | None
    created_at: datetime


class DeliverabilityDetailSchema(Schema):
    """Schema for detailed deliverability responses."""

    id: int
    tenant_id: str
    domain: str
    spf_configured: bool
    spf_valid: bool
    dkim_configured: bool
    dkim_valid: bool
    dmarc_configured: bool
    dmarc_policy: str
    bimi_configured: bool
    reputation_score: Decimal
    reputation_grade: str
    bounce_rate: Decimal
    spam_complaint_rate: Decimal
    blacklist_status: dict[str, Any]
    volume_24h: int
    volume_7d: int
    volume_30d: int
    inbox_placement_pct: Decimal | None
    checked_at: datetime | None
    recommendations: list[str]
    created_at: datetime
    updated_at: datetime


class BounceClassifySchema(Schema):
    """Schema for bounce classification."""

    bounce_code: str
    retry_count: int = 0


class ReputationCalcSchema(Schema):
    """Schema for reputation calculation input."""

    bounce_rate: float = 0.0
    spam_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    unsubscribe_rate: float = 0.0
    blacklisted: bool = False


class AuthCheckSchema(Schema):
    """Schema for authentication check."""

    domain: str
