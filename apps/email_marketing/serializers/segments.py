"""Audience Segment schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Schema


class AudienceSegmentCreateSchema(Schema):
    """Schema for creating an audience segment."""

    tenant_id: str
    name: str
    segment_type: str = "static"
    rules: dict[str, Any] = {}
    description: str = ""
    rfm_enabled: bool = False
    rfm_config: dict[str, Any] = {}
    predictive_type: str = "none"


class AudienceSegmentUpdateSchema(Schema):
    """Schema for updating an audience segment."""

    name: str | None = None
    segment_type: str | None = None
    rules: dict[str, Any] | None = None
    description: str | None = None
    rfm_enabled: bool | None = None
    rfm_config: dict[str, Any] | None = None
    predictive_type: str | None = None


class AudienceSegmentListSchema(Schema):
    """Schema for segment list responses."""

    id: int
    tenant_id: str
    name: str
    segment_type: str
    subscriber_count: int
    last_calculated: datetime | None
    predictive_type: str
    is_system: bool
    created_at: datetime


class AudienceSegmentDetailSchema(Schema):
    """Schema for detailed segment responses."""

    id: int
    tenant_id: str
    name: str
    segment_type: str
    rules: dict[str, Any]
    subscriber_count: int
    last_calculated: datetime | None
    description: str
    rfm_enabled: bool
    rfm_config: dict[str, Any]
    predictive_type: str
    is_system: bool
    created_at: datetime
    updated_at: datetime


class SegmentRefreshSchema(Schema):
    """Schema for segment evaluation."""

    limit: int = 1000


class SubscriberIdsSchema(Schema):
    """Schema for setting static subscriber IDs."""

    subscriber_ids: list[int]
