"""Email campaign management service.

Handles campaign scheduling, validation, recipient resolution,
and real-time statistics updates.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from django.db import transaction

from apps.email_marketing.models.campaign import EmailCampaign
from apps.email_marketing.models.segment import AudienceSegment
from apps.email_marketing.models.subscriber import EmailSubscriber


def validate_campaign_ready(campaign: EmailCampaign) -> list[str]:
    """Validate that a campaign is ready to send.

    Checks subject line, template, from email, and target segment.

    Args:
        campaign: The email campaign to validate.

    Returns:
        List of validation error messages. Empty list means ready.
    """
    errors: list[str] = []
    if not campaign.subject_line or not campaign.subject_line.strip():
        errors.append("Subject line is required")
    if not campaign.template_id:
        errors.append("Email template is required")
    if not campaign.from_email or "@" not in campaign.from_email:
        errors.append("Valid from email is required")
    recipient_count = get_campaign_recipient_count(campaign)
    if recipient_count == 0:
        errors.append("No recipients match the target segment")
    if campaign.status not in (
        EmailCampaign.Status.DRAFT,
        EmailCampaign.Status.SCHEDULED,
    ):
        errors.append(f"Campaign status '{campaign.status}' does not allow sending")
    return errors


def get_campaign_recipient_count(campaign: EmailCampaign) -> int:
    """Count subscribers who would receive this campaign.

    Resolves the campaign's target segment and counts
    mailable (active) subscribers.

    Args:
        campaign: The email campaign.

    Returns:
        Number of mailable recipients.
    """
    if campaign.segment_id_ref:
        try:
            segment = AudienceSegment.objects.get(
                tenant_id=campaign.tenant_id,
                id=campaign.segment_id_ref,
            )
            if segment.segment_type == AudienceSegment.Type.STATIC:
                subscriber_ids = segment.rules.get("subscriber_ids", [])
                return EmailSubscriber.objects.filter(
                    tenant_id=campaign.tenant_id,
                    id__in=subscriber_ids,
                    status=EmailSubscriber.Status.ACTIVE,
                ).count()
            return EmailSubscriber.objects.filter(
                tenant_id=campaign.tenant_id,
                status=EmailSubscriber.Status.ACTIVE,
            ).count()
        except AudienceSegment.DoesNotExist:
            return 0
    return EmailSubscriber.objects.filter(
        tenant_id=campaign.tenant_id,
        status=EmailSubscriber.Status.ACTIVE,
    ).count()


def get_campaign_recipients(
    campaign: EmailCampaign,
    offset: int = 0,
    limit: int = 1000,
) -> list[EmailSubscriber]:
    """Fetch a batch of recipients for a campaign.

    Args:
        campaign: The email campaign.
        offset: Query offset.
        limit: Max subscribers to return.

    Returns:
        List of mailable EmailSubscriber objects.
    """
    queryset = EmailSubscriber.objects.filter(
        tenant_id=campaign.tenant_id,
        status=EmailSubscriber.Status.ACTIVE,
    )
    if campaign.segment_id_ref:
        try:
            segment = AudienceSegment.objects.get(
                tenant_id=campaign.tenant_id,
                id=campaign.segment_id_ref,
            )
            if segment.segment_type == AudienceSegment.Type.STATIC and segment.rules.get(
                "subscriber_ids"
            ):
                queryset = queryset.filter(
                    id__in=segment.rules["subscriber_ids"],
                )
        except AudienceSegment.DoesNotExist:
            return []
    return list(queryset.order_by("id")[offset : offset + limit])


def schedule_campaign(
    campaign: EmailCampaign,
    scheduled_at: datetime,
) -> dict[str, Any]:
    """Schedule a campaign for future sending.

    Args:
        campaign: The email campaign.
        scheduled_at: When to send.

    Returns:
        Dict with status and any errors.
    """
    errors = validate_campaign_ready(campaign)
    if errors:
        return {"success": False, "errors": errors}
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=UTC)
    campaign.scheduled_at = scheduled_at
    campaign.status = EmailCampaign.Status.SCHEDULED
    campaign.save(update_fields=["scheduled_at", "status", "updated_at"])
    return {
        "success": True,
        "campaign_id": str(campaign.id),
        "scheduled_at": campaign.scheduled_at.isoformat(),
    }


def mark_campaign_sending(campaign: EmailCampaign) -> None:
    """Mark campaign as currently sending.

    Args:
        campaign: The email campaign.
    """
    campaign.status = EmailCampaign.Status.SENDING
    campaign.sent_at = datetime.now(UTC)
    campaign.save(update_fields=["status", "sent_at", "updated_at"])


def mark_campaign_sent(campaign: EmailCampaign) -> None:
    """Mark campaign as fully sent.

    Args:
        campaign: The email campaign.
    """
    campaign.status = EmailCampaign.Status.SENT
    campaign.send_progress_pct = 100
    campaign.save(update_fields=["status", "send_progress_pct", "updated_at"])


@transaction.atomic
def update_campaign_stats(
    campaign_id: int,
    field: str,
    increment: int = 1,
) -> dict[str, Any]:
    """Atomically increment a campaign stat counter.

    Args:
        campaign_id: The campaign primary key.
        field: Field name to increment.
        increment: Amount to increment by.

    Returns:
        Dict with updated value.
    """
    try:
        campaign = EmailCampaign.objects.select_for_update().get(id=campaign_id)
        current = getattr(campaign, field, 0) or 0
        setattr(campaign, field, current + increment)
        campaign.save(update_fields=[field, "updated_at"])
        return {"success": True, "field": field, "new_value": current + increment}
    except EmailCampaign.DoesNotExist:
        return {"success": False, "error": "Campaign not found"}


def get_campaign_performance_summary(campaign: EmailCampaign) -> dict[str, Any]:
    """Get a complete performance summary for a campaign.

    Args:
        campaign: The email campaign.

    Returns:
        Dict with all key performance metrics.
    """
    return {
        "campaign_id": str(campaign.id),
        "name": campaign.name,
        "status": campaign.status,
        "total_recipients": campaign.total_recipients,
        "delivered": campaign.delivered,
        "delivery_rate": campaign.delivery_rate,
        "opens": campaign.opens,
        "unique_opens": campaign.unique_opens,
        "open_rate": campaign.open_rate,
        "clicks": campaign.clicks,
        "unique_clicks": campaign.unique_clicks,
        "click_rate": campaign.click_rate,
        "ctr": campaign.ctr,
        "bounces": campaign.bounces,
        "hard_bounces": campaign.hard_bounces,
        "bounce_rate": campaign.bounce_rate,
        "spam_complaints": campaign.spam_complaints,
        "complaint_rate": campaign.complaint_rate,
        "unsubscribes": campaign.unsubscribes,
        "unsubscribe_rate": campaign.unsubscribe_rate,
        "revenue": float(campaign.revenue),
    }
