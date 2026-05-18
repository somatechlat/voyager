"""Campaign budget views.

Pacing calculation, spend recording, allocation, and alert endpoints.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.campaigns.models import Campaign, CampaignBudget
from apps.campaigns.serializers import (
    BudgetAllocationSchema,
    BudgetAlertSchema,
    BudgetSpendSchema,
    PacingResultSchema,
)
from apps.campaigns.services.budget import (
    calculate_pacing,
    check_budget_alerts,
    record_allocation,
    record_spend,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/{campaign_id}/pacing", response=PacingResultSchema)
def get_pacing(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Get budget pacing calculation for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Pacing result dict.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return calculate_pacing(campaign)


@router.get("/{campaign_id}/alerts", response=list[BudgetAlertSchema])
def get_alerts(
    request,
    campaign_id: int,
) -> list[dict[str, Any]]:
    """Check budget alerts for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        List of alert dicts.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return check_budget_alerts(campaign)


@router.post("/{campaign_id}/spend")
def post_spend(
    request,
    campaign_id: int,
    payload: BudgetSpendSchema,
) -> dict[str, Any]:
    """Record a spend transaction.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        payload: Spend data.

    Returns:
        Created entry.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    entry = record_spend(
        campaign=campaign,
        amount=float(payload.amount),
        channel=payload.channel,
        description=payload.description,
        metadata=payload.metadata,
    )
    return {
        "success": True,
        "entry_id": entry.id,
        "amount": float(payload.amount),
        "current_spend": float(campaign.current_spend),
    }


@router.post("/{campaign_id}/allocate")
def post_allocation(
    request,
    campaign_id: int,
    payload: BudgetAllocationSchema,
) -> dict[str, Any]:
    """Record a budget allocation.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        payload: Allocation data.

    Returns:
        Created entry.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    entry = record_allocation(
        campaign=campaign,
        amount=float(payload.amount),
        description=payload.description,
    )
    return {
        "success": True,
        "entry_id": entry.id,
        "amount": float(payload.amount),
        "total_budget": float(campaign.budget) if campaign.budget else 0,
    }


@router.get("/{campaign_id}/history")
def get_budget_history(
    request,
    campaign_id: int,
    type: str = "",
    channel: str = "",
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get budget history for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        type: Filter by entry type.
        channel: Filter by channel.
        limit: Max results.

    Returns:
        List of budget entries.
    """
    qs = CampaignBudget.objects.filter(campaign_id=campaign_id)
    if type:
        qs = qs.filter(type=type)
    if channel:
        qs = qs.filter(channel=channel)

    entries = qs.order_by("-created_at")[:limit]
    return [
        {
            "id": e.id,
            "amount": float(e.amount),
            "type": e.type,
            "channel": e.channel,
            "description": e.description,
            "metadata": e.metadata,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]
