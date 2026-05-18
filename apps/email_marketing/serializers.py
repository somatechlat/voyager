"""Email Marketing schemas (Django Ninja).

Request/response models for templates, campaigns, automation, segments,
deliverability, A/B testing, analytics, and subscribers.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ninja import Schema

# ---------------------------------------------------------------------------
# Email Template schemas
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Email Campaign schemas
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Automation Sequence schemas
# ---------------------------------------------------------------------------


class AutomationSequenceCreateSchema(Schema):
    """Schema for creating an automation sequence."""

    tenant_id: str
    name: str
    trigger_type: str = "list_signup"
    trigger_config: dict[str, Any] = {}
    steps: list[dict[str, Any]] = []
    entry_criteria: dict[str, Any] = {}
    exit_criteria: dict[str, Any] = {}
    frequency_cap: int = 0


class AutomationSequenceUpdateSchema(Schema):
    """Schema for updating an automation sequence."""

    name: str | None = None
    trigger_type: str | None = None
    trigger_config: dict[str, Any] | None = None
    steps: list[dict[str, Any]] | None = None
    status: str | None = None
    entry_criteria: dict[str, Any] | None = None
    exit_criteria: dict[str, Any] | None = None
    frequency_cap: int | None = None


class AutomationSequenceListSchema(Schema):
    """Schema for sequence list responses."""

    id: int
    tenant_id: str
    name: str
    trigger_type: str
    status: str
    total_enrolled: int
    total_completed: int
    step_count: int
    created_at: datetime


class AutomationSequenceDetailSchema(Schema):
    """Schema for detailed sequence responses."""

    id: int
    tenant_id: str
    name: str
    trigger_type: str
    trigger_config: dict[str, Any]
    steps: list[dict[str, Any]]
    status: str
    total_enrolled: int
    total_completed: int
    total_exited: int
    completion_rate: float
    entry_criteria: dict[str, Any]
    exit_criteria: dict[str, Any]
    frequency_cap: int
    created_at: datetime
    updated_at: datetime


class AutomationTriggerSchema(Schema):
    """Schema for testing a trigger."""

    subscriber_id: int
    event_data: dict[str, Any] = {}


class SequenceEvaluateSchema(Schema):
    """Schema for evaluating a sequence step."""

    subscriber_id: int
    step_id: str
    event_data: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Audience Segment schemas
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Deliverability schemas
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# A/B Test schemas
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Analytics schemas
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Subscriber schemas
# ---------------------------------------------------------------------------


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
