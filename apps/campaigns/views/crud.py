"""Campaign CRUD views.

List, create, retrieve, update, delete, and clone campaign endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router

from apps.campaigns.models import Campaign, CampaignChannel
from apps.campaigns.serializers import (
    CampaignCreateSchema,
    CampaignDetailSchema,
    CampaignListSchema,
    CampaignUpdateSchema,
    ChannelCreateSchema,
    ChannelListSchema,
    ChannelUpdateSchema,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/", response=list[CampaignListSchema])
def list_campaigns(
    request,
    tenant_id: str = "",
    client_id: int | None = None,
    stage: str = "",
    status: str = "",
    objective: str = "",
    search: str = "",
    limit: int = 50,
    offset: int = 0,
) -> list[Campaign]:
    """List campaigns with optional filtering.

    Args:
        request: HTTP request.
        tenant_id: Filter by tenant.
        client_id: Filter by client.
        stage: Filter by lifecycle stage.
        status: Filter by status.
        objective: Filter by objective.
        search: Search in name/description.
        limit: Page size.
        offset: Pagination offset.

    Returns:
        List of campaigns.
    """
    qs = Campaign.objects.select_related("client").all()

    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    if client_id:
        qs = qs.filter(client_id=client_id)
    if stage:
        qs = qs.filter(stage=stage)
    if status:
        qs = qs.filter(status=status)
    if objective:
        qs = qs.filter(objective=objective)
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

    return list(qs.order_by("-created_at")[offset : offset + limit])


@router.post("/", response=CampaignDetailSchema)
def create_campaign(
    request,
    payload: CampaignCreateSchema,
) -> Campaign:
    """Create a new campaign.

    Args:
        request: HTTP request.
        payload: Campaign data.

    Returns:
        Created campaign.
    """
    campaign = Campaign.objects.create(
        tenant_id=getattr(request, "tenant_id", "default"),
        client_id=payload.client_id,
        name=payload.name,
        description=payload.description,
        objective=payload.objective,
        start_date=payload.start_date,
        end_date=payload.end_date,
        budget=payload.budget,
        currency=payload.currency,
        pacing_type=payload.pacing_type,
        attribution_model=payload.attribution_model,
        channels=payload.channels,
        target_audience=payload.target_audience,
        kpis=payload.kpis,
        created_by=getattr(request, "user_id", ""),
    )
    logger.info("Created campaign %s: %s", campaign.id, campaign.name)
    return campaign


@router.get("/{campaign_id}", response=CampaignDetailSchema)
def get_campaign(
    request,
    campaign_id: int,
) -> Campaign:
    """Get a single campaign by ID.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Campaign instance.
    """
    return get_object_or_404(Campaign, id=campaign_id)


@router.put("/{campaign_id}", response=CampaignDetailSchema)
def update_campaign(
    request,
    campaign_id: int,
    payload: CampaignUpdateSchema,
) -> Campaign:
    """Update a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        payload: Update data.

    Returns:
        Updated campaign.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)

    update_fields: list[str] = ["updated_at"]
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None and hasattr(campaign, field):
            setattr(campaign, field, value)
            update_fields.append(field)

    campaign.save(update_fields=list(set(update_fields)))
    logger.info("Updated campaign %s", campaign_id)
    return campaign


@router.delete("/{campaign_id}")
def delete_campaign(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Delete a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Deletion confirmation.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    name = campaign.name
    campaign.delete()
    logger.info("Deleted campaign %s: %s", campaign_id, name)
    return {"success": True, "deleted_id": campaign_id, "name": name}


@router.post("/{campaign_id}/clone", response=CampaignDetailSchema)
def clone_campaign(
    request,
    campaign_id: int,
    new_name: str = "",
    include_creatives: bool = True,
    include_audiences: bool = True,
    include_budget: bool = False,
    include_schedule: bool = False,
    include_settings: bool = True,
    reset_performance: bool = True,
) -> Campaign:
    """Clone an existing campaign.

    Args:
        request: HTTP request.
        campaign_id: Source campaign ID.
        new_name: Name for the cloned campaign.
        include_creatives: Copy creative configuration.
        include_audiences: Reference audience definitions.
        include_budget: Copy budget amount.
        include_schedule: Copy schedule dates.
        include_settings: Copy channel/target settings.
        reset_performance: Reset performance data.

    Returns:
        Cloned campaign.
    """
    source = get_object_or_404(Campaign, id=campaign_id)

    clone = Campaign.objects.create(
        tenant_id=source.tenant_id,
        client=source.client,
        name=new_name or f"{source.name} (Copy)",
        description=source.description,
        objective=source.objective,
        stage=Campaign.Stage.PLANNING,
        status=Campaign.Status.DRAFT,
        budget=source.budget if include_budget else None,
        current_spend=0,
        currency=source.currency,
        pacing_type=source.pacing_type if include_settings else Campaign.PacingType.EVEN,
        attribution_model=(
            source.attribution_model if include_settings else Campaign.AttributionModel.LAST_TOUCH
        ),
        channels=source.channels if include_settings else [],
        target_audience=source.target_audience if include_audiences else {},
        kpis=source.kpis if include_settings else {},
        cloned_from=source,
        brief_approved=False,
        all_creatives_approved=False,
        approval_status=Campaign.ApprovalStatus.PENDING,
        all_platforms_published=False,
        alerts_sent={},
        created_by=getattr(request, "user_id", ""),
        start_date=source.start_date if include_schedule else None,
        end_date=source.end_date if include_schedule else None,
    )

    # Clone channels if settings included
    if include_settings:
        for ch in source.channel_configs.all():
            CampaignChannel.objects.create(
                campaign=clone,
                channel_type=ch.channel_type,
                platform=ch.platform,
                config=ch.config if include_creatives else {},
                daily_budget=ch.daily_budget if include_budget else None,
                total_spend=0,
                status=CampaignChannel.Status.PENDING,
                start_date=ch.start_date if include_schedule else None,
                end_date=ch.end_date if include_schedule else None,
                dependencies=ch.dependencies,
                lead_time_days=ch.lead_time_days,
            )

    logger.info("Cloned campaign %s -> %s", campaign_id, clone.id)
    return clone


# ---------------------------------------------------------------------------
# Campaign channel CRUD (nested under campaign)
# ---------------------------------------------------------------------------


@router.get("/{campaign_id}/channels", response=list[ChannelListSchema])
def list_channels(
    request,
    campaign_id: int,
) -> list[CampaignChannel]:
    """List channels for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        List of channels.
    """
    return list(CampaignChannel.objects.filter(campaign_id=campaign_id))


@router.post("/{campaign_id}/channels", response=ChannelListSchema)
def create_channel(
    request,
    campaign_id: int,
    payload: ChannelCreateSchema,
) -> CampaignChannel:
    """Add a channel to a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        payload: Channel data.

    Returns:
        Created channel.
    """
    get_object_or_404(Campaign, id=campaign_id)
    channel = CampaignChannel.objects.create(
        campaign_id=campaign_id,
        channel_type=payload.channel_type,
        platform=payload.platform,
        config=payload.config,
        daily_budget=payload.daily_budget,
        start_date=payload.start_date,
        end_date=payload.end_date,
        dependencies=payload.dependencies,
        lead_time_days=payload.lead_time_days,
    )
    logger.info("Created channel %s for campaign %s", channel.id, campaign_id)
    return channel


@router.put("/{campaign_id}/channels/{channel_id}", response=ChannelListSchema)
def update_channel(
    request,
    campaign_id: int,
    channel_id: int,
    payload: ChannelUpdateSchema,
) -> CampaignChannel:
    """Update a campaign channel.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        channel_id: Channel ID.
        payload: Update data.

    Returns:
        Updated channel.
    """
    channel = get_object_or_404(CampaignChannel, id=channel_id, campaign_id=campaign_id)

    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None and hasattr(channel, field):
            setattr(channel, field, value)

    channel.save()
    return channel


@router.delete("/{campaign_id}/channels/{channel_id}")
def delete_channel(
    request,
    campaign_id: int,
    channel_id: int,
) -> dict[str, Any]:
    """Delete a campaign channel.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        channel_id: Channel ID.

    Returns:
        Deletion confirmation.
    """
    channel = get_object_or_404(CampaignChannel, id=channel_id, campaign_id=campaign_id)
    channel.delete()
    return {"success": True, "deleted_id": channel_id}
