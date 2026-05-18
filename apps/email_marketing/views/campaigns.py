"""Email campaign management views."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.email_marketing.models.campaign import EmailCampaign
from apps.email_marketing.serializers import (
    CampaignPerformanceSchema,
    EmailCampaignCreateSchema,
    EmailCampaignDetailSchema,
    EmailCampaignListSchema,
    EmailCampaignScheduleSchema,
    EmailCampaignUpdateSchema,
)
from apps.email_marketing.services.campaigns import (
    get_campaign_performance_summary,
    validate_campaign_ready,
)
from apps.email_marketing.tasks import send_campaign_emails

logger = logging.getLogger(__name__)

router = Router()


@router.get("/", response=list[EmailCampaignListSchema])
def list_campaigns(
    request,
    tenant_id: str = "",
    status: str = "",
    search: str = "",
    limit: int = 50,
    offset: int = 0,
) -> list[EmailCampaign]:
    """List email campaigns with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        status: Filter by campaign status.
        search: Search in name.
        limit: Page size.
        offset: Pagination offset.

    Returns:
        List of email campaigns.
    """
    qs = EmailCampaign.objects.select_related("template").all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(name__icontains=search)
    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.post("/", response=EmailCampaignDetailSchema)
def create_campaign(
    request,
    payload: EmailCampaignCreateSchema,
) -> EmailCampaign:
    """Create a new email campaign.

    Args:
        request: HTTP request.
        payload: Campaign creation data.

    Returns:
        Created campaign.
    """
    data = payload.dict()
    campaign = EmailCampaign.objects.create(**data)
    logger.info("Campaign %s created for tenant %s", campaign.id, campaign.tenant_id)
    return campaign


@router.get("/{campaign_id}", response=EmailCampaignDetailSchema)
def get_campaign(
    request,
    campaign_id: int,
) -> EmailCampaign:
    """Get a single email campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.

    Returns:
        Email campaign.
    """
    return get_object_or_404(EmailCampaign.objects.select_related("template"), id=campaign_id)


@router.put("/{campaign_id}", response=EmailCampaignDetailSchema)
def update_campaign(
    request,
    campaign_id: int,
    payload: EmailCampaignUpdateSchema,
) -> EmailCampaign:
    """Update an email campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.
        payload: Update data.

    Returns:
        Updated campaign.
    """
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    data = payload.dict(exclude_unset=True)
    for attr, val in data.items():
        setattr(campaign, attr, val)
    campaign.save()
    return campaign


@router.delete("/{campaign_id}")
def delete_campaign(
    request,
    campaign_id: int,
) -> dict[str, bool]:
    """Delete an email campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.

    Returns:
        Success dict.
    """
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    campaign.delete()
    return {"success": True}


@router.post("/{campaign_id}/schedule")
def schedule_campaign_endpoint(
    request,
    campaign_id: int,
    payload: EmailCampaignScheduleSchema,
) -> dict[str, Any]:
    """Schedule a campaign for future sending.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.
        payload: Schedule data.

    Returns:
        Schedule result dict.
    """
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    errors = validate_campaign_ready(campaign)
    if errors:
        return {"success": False, "errors": errors}
    scheduled_at = payload.scheduled_at
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=UTC)
    campaign.scheduled_at = scheduled_at
    campaign.status = EmailCampaign.Status.SCHEDULED
    campaign.save(update_fields=["scheduled_at", "status"])
    return {
        "success": True,
        "campaign_id": str(campaign.id),
        "scheduled_at": campaign.scheduled_at.isoformat(),
    }


@router.post("/{campaign_id}/send")
def send_campaign_now(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Send a campaign immediately via Celery task.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.

    Returns:
        Task dispatch result.
    """
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    errors = validate_campaign_ready(campaign)
    if errors:
        return {"success": False, "errors": errors}
    campaign.status = EmailCampaign.Status.SENDING
    campaign.sent_at = datetime.now(UTC)
    campaign.save(update_fields=["status", "sent_at"])
    task = send_campaign_emails.delay(
        campaign_id=str(campaign.id),
        tenant_id=campaign.tenant_id,
        batch_size=1000,
    )
    logger.info("Campaign %s send task dispatched: %s", campaign.id, task.id)
    return {"success": True, "task_id": task.id, "status": "dispatched"}


@router.post("/{campaign_id}/cancel")
def cancel_campaign(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Cancel a scheduled or draft campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.

    Returns:
        Cancel result.
    """
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    if campaign.status not in (EmailCampaign.Status.DRAFT, EmailCampaign.Status.SCHEDULED):
        return {"success": False, "error": f"Cannot cancel campaign in status: {campaign.status}"}
    campaign.status = EmailCampaign.Status.CANCELLED
    campaign.save(update_fields=["status"])
    return {"success": True, "campaign_id": str(campaign.id), "status": campaign.status}


@router.get("/{campaign_id}/performance", response=CampaignPerformanceSchema)
def get_performance(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Get performance summary for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign primary key.

    Returns:
        Performance metrics dict.
    """
    campaign = get_object_or_404(EmailCampaign, id=campaign_id)
    return get_campaign_performance_summary(campaign)
