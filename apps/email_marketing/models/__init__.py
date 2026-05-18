"""Email Marketing models package.

Exports all models for the email marketing module.
"""

from apps.email_marketing.models.ab_test import EmailABTest
from apps.email_marketing.models.analytics import EmailAnalytics
from apps.email_marketing.models.campaign import EmailCampaign
from apps.email_marketing.models.deliverability import DeliverabilityMonitor
from apps.email_marketing.models.segment import AudienceSegment
from apps.email_marketing.models.sequence import AutomationSequence
from apps.email_marketing.models.subscriber import EmailSubscriber
from apps.email_marketing.models.template import EmailTemplate

__all__ = [
    "EmailSubscriber",
    "EmailTemplate",
    "EmailCampaign",
    "AutomationSequence",
    "AudienceSegment",
    "DeliverabilityMonitor",
    "EmailABTest",
    "EmailAnalytics",
]
