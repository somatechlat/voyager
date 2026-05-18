"""Email Campaign schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from ninja import Schema


class EmailCampaignCreateSchema(Schema):
    """Schema for creating an email campaign."""

    tenant_id: str
    name: str
    subject_line: str = ""
    preview_text: str = ""
    from_name: str = ""
    from_email: str = ""
    reply_to: str = ""
    template_id: int | None = None
    segment_id_ref: str = ""
    status: str = "draft"
    scheduled_at: datetime | None = None
    total_recipients: int = 0


class EmailCampaignUpdateSchema(Schema):
    """Schema for updating an email campaign."""

    name: str | None = None
    subject_line: str | None = None
    preview_text: str | None = None
    from_name: str | None = None
    from_email: str | None = None
    reply_to: str | None = None
    template_id: int | None = None
    segment_id_ref: str | None = None
    status: str | None = None
    scheduled_at: datetime | None = None


class EmailCampaignListSchema(Schema):
    """Schema for campaign list responses."""

    id: int
    tenant_id: str
    name: str
    subject_line: str
    from_email: str
    status: str
    scheduled_at: datetime | None
    sent_at: datetime | None
    total_recipients: int
    delivered: int
    opens: int
    clicks: int
    revenue: Decimal
    created_at: datetime


class EmailCampaignDetailSchema(Schema):
    """Schema for detailed campaign responses."""

    id: int
    tenant_id: str
    name: str
    subject_line: str
    preview_text: str
    from_name: str
    from_email: str
    reply_to: str
    template_id: int | None
    segment_id_ref: str
    status: str
    scheduled_at: datetime | None
    sent_at: datetime | None
    total_recipients: int
    delivered: int
    opens: int
    unique_opens: int
    clicks: int
    unique_clicks: int
    bounces: int
    hard_bounces: int
    spam_complaints: int
    unsubscribes: int
    revenue: Decimal
    send_progress_pct: Decimal
    created_at: datetime
    updated_at: datetime


class EmailCampaignScheduleSchema(Schema):
    """Schema for scheduling a campaign."""

    scheduled_at: datetime


class CampaignPerformanceSchema(Schema):
    """Schema for campaign performance summary."""

    campaign_id: str
    name: str
    status: str
    total_recipients: int
    delivered: int
    delivery_rate: float
    opens: int
    unique_opens: int
    open_rate: float
    clicks: int
    unique_clicks: int
    click_rate: float
    ctr: float
    bounces: int
    hard_bounces: int
    bounce_rate: float
    spam_complaints: int
    complaint_rate: float
    unsubscribes: int
    unsubscribe_rate: float
    revenue: float
