"""Email Template schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema


class EmailTemplateCreateSchema(Schema):
    """Schema for creating an email template."""

    tenant_id: str
    name: str
    category: str = "custom"
    html: str = ""
    json_design: dict[str, Any] = {}
    blocks: list[dict[str, Any]] | None = None
    thumbnail: str = ""
    is_amp: bool = False
    brand_kit: dict[str, Any] = {}
    preheader_text: str = ""


class EmailTemplateUpdateSchema(Schema):
    """Schema for updating an email template."""

    name: str | None = None
    category: str | None = None
    html: str | None = None
    json_design: dict[str, Any] | None = None
    blocks: list[dict[str, Any]] | None = None
    thumbnail: str | None = None
    is_amp: bool | None = None
    brand_kit: dict[str, Any] | None = None
    preheader_text: str | None = None


class EmailTemplateListSchema(Schema):
    """Schema for email template list responses."""

    id: int
    tenant_id: str
    name: str
    category: str
    thumbnail: str
    is_amp: bool
    compatibility_score: Decimal | None
    created_at: datetime
    updated_at: datetime


class EmailTemplateDetailSchema(Schema):
    """Schema for detailed email template responses."""

    id: int
    tenant_id: str
    name: str
    category: str
    html: str
    json_design: dict[str, Any]
    thumbnail: str
    is_amp: bool
    brand_kit: dict[str, Any]
    preheader_text: str
    compatibility_score: Decimal | None
    compatibility_results: dict[str, Any]
    plain_text: str
    created_at: datetime
    updated_at: datetime


class EmailTemplateRenderSchema(Schema):
    """Schema for rendering a template."""

    preheader: str = ""
    brand_kit: dict[str, Any] | None = None


class CompatibilityResultSchema(Schema):
    """Schema for compatibility test results."""

    overall_score: float
    clients: list[dict[str, Any]]
