"""Email Marketing schemas (Django Ninja).

Request/response models for templates, campaigns, automation, segments,
deliverability, A/B testing, analytics, and subscribers.
"""

from __future__ import annotations

from .ab_tests import (
    ABTestResultSchema,
    EmailABTestCreateSchema,
    EmailABTestDetailSchema,
    EmailABTestListSchema,
    EmailABTestUpdateSchema,
    SampleSizeCalcSchema,
    WinnerSelectSchema,
)
from .analytics import (
    DeviceBreakdownSchema,
    EmailAnalyticsDetailSchema,
    EmailAnalyticsListSchema,
    EngagementTierSchema,
    HeatmapGenerateSchema,
    HourlyBreakdownSchema,
)
from .automation import (
    AutomationSequenceCreateSchema,
    AutomationSequenceDetailSchema,
    AutomationSequenceListSchema,
    AutomationSequenceUpdateSchema,
    AutomationTriggerSchema,
    SequenceEvaluateSchema,
)
from .campaigns import (
    CampaignPerformanceSchema,
    EmailCampaignCreateSchema,
    EmailCampaignDetailSchema,
    EmailCampaignListSchema,
    EmailCampaignScheduleSchema,
    EmailCampaignUpdateSchema,
)
from .deliverability import (
    AuthCheckSchema,
    BounceClassifySchema,
    DeliverabilityCreateSchema,
    DeliverabilityDetailSchema,
    DeliverabilityListSchema,
    DeliverabilityUpdateSchema,
    ReputationCalcSchema,
)
from .segments import (
    AudienceSegmentCreateSchema,
    AudienceSegmentDetailSchema,
    AudienceSegmentListSchema,
    AudienceSegmentUpdateSchema,
    SegmentRefreshSchema,
    SubscriberIdsSchema,
)
from .subscribers import (
    EmailSubscriberCreateSchema,
    EmailSubscriberDetailSchema,
    EmailSubscriberListSchema,
    EmailSubscriberUpdateSchema,
    SubscriberBulkSchema,
    SubscriberSuppressSchema,
    SubscriberTagSchema,
)
from .templates import (
    CompatibilityResultSchema,
    EmailTemplateCreateSchema,
    EmailTemplateDetailSchema,
    EmailTemplateListSchema,
    EmailTemplateRenderSchema,
    EmailTemplateUpdateSchema,
)

__all__ = [
    # Templates
    "EmailTemplateCreateSchema",
    "EmailTemplateUpdateSchema",
    "EmailTemplateListSchema",
    "EmailTemplateDetailSchema",
    "EmailTemplateRenderSchema",
    "CompatibilityResultSchema",
    # Campaigns
    "EmailCampaignCreateSchema",
    "EmailCampaignUpdateSchema",
    "EmailCampaignListSchema",
    "EmailCampaignDetailSchema",
    "EmailCampaignScheduleSchema",
    "CampaignPerformanceSchema",
    # Automation
    "AutomationSequenceCreateSchema",
    "AutomationSequenceUpdateSchema",
    "AutomationSequenceListSchema",
    "AutomationSequenceDetailSchema",
    "AutomationTriggerSchema",
    "SequenceEvaluateSchema",
    # Segments
    "AudienceSegmentCreateSchema",
    "AudienceSegmentUpdateSchema",
    "AudienceSegmentListSchema",
    "AudienceSegmentDetailSchema",
    "SegmentRefreshSchema",
    "SubscriberIdsSchema",
    # Deliverability
    "DeliverabilityCreateSchema",
    "DeliverabilityUpdateSchema",
    "DeliverabilityListSchema",
    "DeliverabilityDetailSchema",
    "BounceClassifySchema",
    "ReputationCalcSchema",
    "AuthCheckSchema",
    # A/B Tests
    "EmailABTestCreateSchema",
    "EmailABTestUpdateSchema",
    "EmailABTestListSchema",
    "EmailABTestDetailSchema",
    "SampleSizeCalcSchema",
    "WinnerSelectSchema",
    "ABTestResultSchema",
    # Analytics
    "EmailAnalyticsListSchema",
    "EmailAnalyticsDetailSchema",
    "HeatmapGenerateSchema",
    "EngagementTierSchema",
    "DeviceBreakdownSchema",
    "HourlyBreakdownSchema",
    # Subscribers
    "EmailSubscriberCreateSchema",
    "EmailSubscriberUpdateSchema",
    "EmailSubscriberListSchema",
    "EmailSubscriberDetailSchema",
    "SubscriberBulkSchema",
    "SubscriberTagSchema",
    "SubscriberSuppressSchema",
]
