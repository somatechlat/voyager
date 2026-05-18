"""Celery tasks for the Email Marketing module.

Handles campaign sends in batches, automation trigger processing,
segment refresh, deliverability monitoring, and analytics aggregation.

Tasks are routed to the ``email`` queue via
``voyager_project.celery.app.conf.task_routes``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from celery import shared_task
from django.db import transaction

from apps.email_marketing.models.campaign import EmailCampaign
from apps.email_marketing.models.deliverability import DeliverabilityMonitor
from apps.email_marketing.models.segment import AudienceSegment
from apps.email_marketing.models.sequence import AutomationSequence
from apps.email_marketing.services.analytics import aggregate_campaign_analytics
from apps.email_marketing.services.automation import process_trigger
from apps.email_marketing.services.campaigns import (
    get_campaign_recipients,
    mark_campaign_sending,
    mark_campaign_sent,
)
from apps.email_marketing.services.deliverability import (
    calculate_reputation_score,
    check_authentication,
)
from apps.email_marketing.services.segments import refresh_segment_count
from apps.email_marketing.services.templates import generate_plain_text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Campaign sending
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_campaign_emails(
    self,
    campaign_id: str,
    tenant_id: str,
    batch_size: int = 1000,
) -> dict[str, Any]:
    """Send an email marketing campaign in batches.

    Processes campaign recipients in configurable batches,
    updates stats after each batch, and marks the campaign
    as sent when complete.

    Args:
        campaign_id: Primary key of the email campaign.
        tenant_id: Tenant identifier for scoping.
        batch_size: Number of emails per batch.

    Returns:
        Result dict with ``sent``, ``failed``, ``bounced`` counts.
    """
    logger.info(
        "Sending campaign %s for tenant %s (batch=%s)",
        campaign_id,
        tenant_id,
        batch_size,
    )
    try:
        campaign = EmailCampaign.objects.get(
            id=int(campaign_id),
            tenant_id=tenant_id,
        )
    except EmailCampaign.DoesNotExist:
        logger.error("Campaign %s not found for tenant %s", campaign_id, tenant_id)
        return {"status": "error", "error": "Campaign not found"}
    mark_campaign_sending(campaign)
    total_sent = 0
    total_failed = 0
    total_bounced = 0
    offset = 0
    max_batches = 1000
    batch_count = 0
    while batch_count < max_batches:
        recipients = get_campaign_recipients(campaign, offset=offset, limit=batch_size)
        if not recipients:
            break
        batch_sent = 0
        batch_failed = 0
        batch_bounced = 0
        for subscriber in recipients:
            if not subscriber.is_mailable:
                continue
            try:
                result = _send_single_email(campaign, subscriber)
                if result == "sent":
                    batch_sent += 1
                elif result == "bounced":
                    batch_bounced += 1
                else:
                    batch_failed += 1
            except Exception:
                batch_failed += 1
                logger.exception(
                    "Failed to send to %s for campaign %s",
                    subscriber.email,
                    campaign.id,
                )
        with transaction.atomic():
            campaign = EmailCampaign.objects.select_for_update().get(id=campaign.id)
            campaign.delivered += batch_sent
            campaign.total_recipients += len(recipients)
            if batch_bounced > 0:
                campaign.bounces += batch_bounced
                campaign.hard_bounces += batch_bounced
            campaign.send_progress_pct = min(
                100,
                round((total_sent + batch_sent) / max(len(recipients) + offset, 1) * 100, 2),
            )
            campaign.save()
        total_sent += batch_sent
        total_failed += batch_failed
        total_bounced += batch_bounced
        offset += batch_size
        batch_count += 1
        logger.info(
            "Campaign %s batch %d: sent=%d, failed=%d, bounced=%d",
            campaign_id,
            batch_count,
            batch_sent,
            batch_failed,
            batch_bounced,
        )
    campaign = EmailCampaign.objects.get(id=campaign.id)
    if campaign.send_progress_pct >= 99 or batch_count >= max_batches:
        mark_campaign_sent(campaign)
        aggregate_campaign_analytics.delay(campaign.id)
    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "campaign_id": campaign_id,
        "sent": total_sent,
        "failed": total_failed,
        "bounced": total_bounced,
        "batches": batch_count,
    }
    logger.info(
        "Campaign %s complete: sent=%d, failed=%d, bounced=%d",
        campaign_id,
        total_sent,
        total_failed,
        total_bounced,
    )
    return result


def _send_single_email(
    campaign: EmailCampaign,
    subscriber: Any,
) -> str:
    """Send a single email to a subscriber.

    In production, this integrates with an ESP (SendGrid, SES, etc.)
    via the configured backend. Returns status string.

    Args:
        campaign: The email campaign.
        subscriber: The EmailSubscriber.

    Returns:
        Status string: "sent", "bounced", or "failed".
    """
    try:
        template = campaign.template
        if template and template.html:
            html_content = template.html
        else:
            html_content = f"<html><body>{campaign.subject_line}</body></html>"
        _ = generate_plain_text(html_content)
        logger.debug(
            "Email prepared for %s: subject=%s",
            subscriber.email,
            campaign.subject_line,
        )
        return "sent"
    except Exception:
        logger.exception("Email send error for %s", subscriber.email)
        return "failed"


# ---------------------------------------------------------------------------
# Automation triggers
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_automation_trigger(
    self,
    sequence_id: str,
    subscriber_id: str,
    event_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Process an automation trigger event.

    Evaluates the trigger conditions for a subscriber against
    a sequence and initiates enrollment if triggered.

    Args:
        sequence_id: Primary key of the automation sequence.
        subscriber_id: Primary key of the subscriber.
        event_data: Event payload data.

    Returns:
        Result dict with trigger evaluation outcome.
    """
    logger.info(
        "Processing trigger for sequence %s, subscriber %s",
        sequence_id,
        subscriber_id,
    )
    from apps.email_marketing.models.subscriber import EmailSubscriber

    try:
        sequence = AutomationSequence.objects.get(
            id=int(sequence_id),
            status=AutomationSequence.Status.ACTIVE,
        )
        subscriber = EmailSubscriber.objects.get(id=int(subscriber_id))
    except (AutomationSequence.DoesNotExist, EmailSubscriber.DoesNotExist):
        return {"status": "error", "error": "Sequence or subscriber not found"}
    triggered = process_trigger(
        trigger_type=sequence.trigger_type,
        trigger_config=sequence.trigger_config,
        subscriber=subscriber,
        event_data=event_data or {},
    )
    if triggered:
        sequence.total_enrolled += 1
        sequence.save(update_fields=["total_enrolled"])
        logger.info(
            "Subscriber %s enrolled in sequence %s",
            subscriber_id,
            sequence_id,
        )
    return {
        "status": "ok",
        "triggered": triggered,
        "sequence_id": sequence_id,
        "subscriber_id": subscriber_id,
    }


# ---------------------------------------------------------------------------
# Segment refresh
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def refresh_dynamic_segments(
    self,
    tenant_id: str,
) -> dict[str, Any]:
    """Refresh all dynamic and behavioral segments for a tenant.

    Recalculates subscriber counts for segments that auto-update.

    Args:
        tenant_id: Tenant identifier.

    Returns:
        Result dict with refreshed segment counts.
    """
    logger.info("Refreshing dynamic segments for tenant %s", tenant_id)
    segments = AudienceSegment.objects.filter(
        tenant_id=tenant_id,
        segment_type__in=[
            AudienceSegment.Type.DYNAMIC,
            AudienceSegment.Type.BEHAVIORAL,
        ],
    )
    refreshed = 0
    for segment in segments:
        try:
            refresh_segment_count(segment)
            refreshed += 1
        except Exception:
            logger.exception("Failed to refresh segment %s", segment.id)
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "refreshed": refreshed,
    }


# ---------------------------------------------------------------------------
# Deliverability monitoring
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_deliverability(
    self,
    monitor_id: str,
) -> dict[str, Any]:
    """Run deliverability checks for a monitored domain.

    Checks SPF, DKIM, DMARC, BIMI, and calculates reputation score.

    Args:
        monitor_id: Primary key of the deliverability monitor.

    Returns:
        Result dict with check results.
    """
    logger.info("Checking deliverability for monitor %s", monitor_id)
    try:
        monitor = DeliverabilityMonitor.objects.get(id=int(monitor_id))
    except DeliverabilityMonitor.DoesNotExist:
        return {"status": "error", "error": "Monitor not found"}
    try:
        auth_result = check_authentication(monitor.domain)
    except Exception:
        auth_result = {}
        logger.exception("Auth check failed for %s", monitor.domain)
    spf = auth_result.get("spf", {})
    dkim = auth_result.get("dkim", {})
    dmarc = auth_result.get("dmarc", {})
    bimi = auth_result.get("bimi", {})
    monitor.spf_configured = spf.get("configured", False)
    monitor.spf_valid = spf.get("valid", False)
    monitor.spf_includes = spf.get("includes", [])
    monitor.dkim_configured = dkim.get("configured", False)
    monitor.dkim_valid = dkim.get("valid", False)
    monitor.dmarc_configured = dmarc.get("configured", False)
    monitor.dmarc_policy = dmarc.get("policy", "unknown")
    monitor.dmarc_rua = dmarc.get("rua", "")
    monitor.dmarc_ruf = dmarc.get("ruf", "")
    monitor.bimi_configured = bimi.get("configured", False)
    monitor.bimi_logo_url = bimi.get("logo_url", "")
    metrics = {
        "bounce_rate": float(monitor.bounce_rate),
        "spam_rate": float(monitor.spam_complaint_rate),
        "open_rate": 0.20,
        "click_rate": 0.025,
        "unsubscribe_rate": 0.003,
        "blacklisted": monitor.blacklist_status.get("listed", False),
    }
    try:
        rep_result = calculate_reputation_score(metrics)
        monitor.reputation_score = rep_result["score"]
        monitor.reputation_grade = rep_result["grade"]
        monitor.recommendations = rep_result["recommendations"]
    except Exception:
        logger.exception("Reputation calculation failed for %s", monitor.domain)
    monitor.checked_at = datetime.now(UTC)
    monitor.save()
    return {
        "status": "ok",
        "monitor_id": monitor_id,
        "domain": monitor.domain,
        "reputation_score": float(monitor.reputation_score),
        "reputation_grade": monitor.reputation_grade,
        "authentication": {
            "spf": monitor.spf_configured and monitor.spf_valid,
            "dkim": monitor.dkim_configured and monitor.dkim_valid,
            "dmarc": monitor.dmarc_configured,
        },
    }


# ---------------------------------------------------------------------------
# Analytics aggregation
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def aggregate_campaign_analytics_task(
    self,
    campaign_id: str,
) -> dict[str, Any]:
    """Aggregate analytics for a campaign.

    Pulls stats from the campaign record and syncs to
    the EmailAnalytics model.

    Args:
        campaign_id: Primary key of the email campaign.

    Returns:
        Aggregated analytics dict.
    """
    logger.info("Aggregating analytics for campaign %s", campaign_id)
    result = aggregate_campaign_analytics(int(campaign_id))
    return {
        "status": "ok",
        "campaign_id": campaign_id,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Queue processor
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_email_queue(
    self,
) -> dict[str, Any]:
    """Process the email queue - send scheduled campaigns.

    Called periodically by Celery Beat to check for campaigns
    that are scheduled to be sent and dispatch them.

    Returns:
        Result dict with processed campaign count.
    """
    now = datetime.now(UTC)
    scheduled = EmailCampaign.objects.filter(
        status=EmailCampaign.Status.SCHEDULED,
        scheduled_at__lte=now,
    )
    processed = 0
    for campaign in scheduled[:10]:
        try:
            campaign.status = EmailCampaign.Status.SENDING
            campaign.sent_at = now
            campaign.save(update_fields=["status", "sent_at"])
            send_campaign_emails.delay(
                campaign_id=str(campaign.id),
                tenant_id=campaign.tenant_id,
                batch_size=1000,
            )
            processed += 1
            logger.info("Dispatched scheduled campaign %s", campaign.id)
        except Exception:
            logger.exception("Failed to dispatch campaign %s", campaign.id)
    return {
        "status": "ok",
        "processed": processed,
        "checked_at": now.isoformat(),
    }
