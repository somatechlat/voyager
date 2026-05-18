"""Campaign lifecycle views.

Stage transitions, validation, and auto-advance endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.campaigns.models import Campaign
from apps.campaigns.serializers import (
    AvailableStageSchema,
    StageTransitionResponseSchema,
    StageTransitionSchema,
)
from apps.campaigns.services.lifecycle import (
    auto_advance_if_eligible,
    get_available_stages,
    transition_stage,
)

logger = logging.getLogger(__name__)

router = Router()


@router.post(
    "/{campaign_id}/transition",
    response=StageTransitionResponseSchema,
)
def stage_transition(
    request,
    campaign_id: int,
    payload: StageTransitionSchema,
) -> dict[str, Any]:
    """Transition a campaign to a new lifecycle stage.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        payload: Target stage.

    Returns:
        Transition result.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    user_id = getattr(request, "user_id", "system")
    result = transition_stage(campaign, payload.target_stage, triggered_by=user_id)
    return result


@router.get(
    "/{campaign_id}/stages",
    response=list[AvailableStageSchema],
)
def list_available_stages(
    request,
    campaign_id: int,
) -> list[dict[str, Any]]:
    """List available stages for a campaign with validation.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        List of available stages.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return get_available_stages(campaign)


@router.post(
    "/{campaign_id}/auto-advance",
    response=StageTransitionResponseSchema,
)
def auto_advance(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Attempt to auto-advance a campaign based on trigger conditions.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Auto-advance result.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return auto_advance_if_eligible(campaign)


@router.post("/{campaign_id}/approve-brief")
def approve_brief(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Mark a campaign brief as approved.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Approval result.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    campaign.brief_approved = True
    campaign.save(update_fields=["brief_approved", "updated_at"])
    return {"success": True, "brief_approved": True}


@router.post("/{campaign_id}/approve-creatives")
def approve_creatives(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Mark all creatives as approved.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Approval result.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    campaign.all_creatives_approved = True
    campaign.save(update_fields=["all_creatives_approved", "updated_at"])
    return {"success": True, "all_creatives_approved": True}


@router.post("/{campaign_id}/stakeholder-approval")
def stakeholder_approval(
    request,
    campaign_id: int,
    status: str,
) -> dict[str, Any]:
    """Set stakeholder approval status.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        status: Approval status (approved, rejected, changes_requested).

    Returns:
        Approval result.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if status not in dict(Campaign.ApprovalStatus.choices):
        return {"success": False, "error": f"Invalid status: {status}"}
    campaign.approval_status = status
    campaign.save(update_fields=["approval_status", "updated_at"])
    return {"success": True, "approval_status": status}


@router.post("/{campaign_id}/publish-platforms")
def publish_platforms(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Mark all platforms as published.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Publish result.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    campaign.all_platforms_published = True
    campaign.save(update_fields=["all_platforms_published", "updated_at"])
    return {"success": True, "all_platforms_published": True}
