"""Subscriber schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class EmailSubscriberCreateSchema(Schema):
    """Schema for creating a subscriber."""

    tenant_id: str
    email: str
    first_name: str = ""
    last_name: str = ""
    status: str = "active"
    source: str = "manual"
    tags: list[str] = []
    custom_fields: dict[str, Any] = {}


class EmailSubscriberUpdateSchema(Schema):
    """Schema for updating a subscriber."""

    first_name: str | None = None
    last_name: str | None = None
    status: str | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None
    engagement_score: Decimal | None = None


class EmailSubscriberListSchema(Schema):
    """Schema for subscriber list responses."""

    id: int
    tenant_id: str
    email: str
    first_name: str
    last_name: str
    status: str
    source: str
    tags: list[str]
    engagement_score: Decimal
    subscribed_at: datetime
    last_opened_at: datetime | None


class EmailSubscriberDetailSchema(Schema):
    """Schema for detailed subscriber responses."""

    id: int
    tenant_id: str
    email: str
    first_name: str
    last_name: str
    full_name: str
    status: str
    source: str
    tags: list[str]
    custom_fields: dict[str, Any]
    engagement_score: Decimal
    subscribed_at: datetime
    unsubscribed_at: datetime | None
    last_opened_at: datetime | None
    last_clicked_at: datetime | None
    open_count: int
    click_count: int
    rfm_recency: int
    rfm_frequency: int
    rfm_monetary: Decimal
    rfm_score: str
    is_mailable: bool
    created_at: datetime
    updated_at: datetime


class SubscriberBulkSchema(Schema):
    """Schema for bulk subscriber operations."""

    subscribers: list[EmailSubscriberCreateSchema]


class SubscriberTagSchema(Schema):
    """Schema for tag operations."""

    tags: list[str]
    operation: str = "set"


class SubscriberSuppressSchema(Schema):
    """Schema for subscriber suppression."""

    reason: str = "suppressed"
