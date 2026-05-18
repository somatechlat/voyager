"""Campaign brief views.

AI-generated brief creation, retrieval, and approval.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.campaigns.models import Campaign, CampaignBrief
from apps.campaigns.serializers import BriefApproveSchema, BriefResponseSchema
from apps.campaigns.services.briefs import generate_brief

logger = logging.getLogger(__name__)

router = Router()


@router.post("/{campaign_id}/briefs/generate", response=BriefResponseSchema)
def generate_brief_endpoint(
    request,
    campaign_id: int,
) -> CampaignBrief:
    """Generate an AI brief for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Generated brief.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    brief = generate_brief(campaign)
    return brief


@router.get("/{campaign_id}/briefs")
def list_briefs(
    request,
    campaign_id: int,
) -> list[dict[str, Any]]:
    """List all briefs for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        List of briefs.
    """
    briefs = CampaignBrief.objects.filter(campaign_id=campaign_id).order_by("-version")
    return [
        {
            "id": b.id,
            "version": b.version,
            "objective_type": b.objective_type,
            "estimated_timeline_days": b.estimated_timeline_days,
            "suggested_budget": b.suggested_budget,
            "is_approved": b.is_approved,
            "approved_by": b.approved_by,
            "created_at": b.created_at.isoformat(),
        }
        for b in briefs
    ]


@router.get("/{campaign_id}/briefs/{brief_id}")
def get_brief(
    request,
    campaign_id: int,
    brief_id: int,
) -> dict[str, Any]:
    """Get a detailed brief.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        brief_id: Brief ID.

    Returns:
        Full brief detail.
    """
    brief = get_object_or_404(CampaignBrief, id=brief_id, campaign_id=campaign_id)
    return {
        "id": brief.id,
        "version": brief.version,
        "objective_type": brief.objective_type,
        "target_metrics": brief.target_metrics,
        "selected_personas": brief.selected_personas,
        "competitive_insights": brief.competitive_insights,
        "recommended_channels": brief.recommended_channels,
        "estimated_timeline_days": brief.estimated_timeline_days,
        "suggested_budget": brief.suggested_budget,
        "executive_summary": brief.executive_summary,
        "objectives_and_kpis": brief.objectives_and_kpis,
        "target_audience_profiles": brief.target_audience_profiles,
        "channel_strategy": brief.channel_strategy,
        "content_requirements": brief.content_requirements,
        "timeline_details": brief.timeline_details,
        "budget_breakdown": brief.budget_breakdown,
        "risk_assessment": brief.risk_assessment,
        "is_approved": brief.is_approved,
        "approved_by": brief.approved_by,
        "approved_at": brief.approved_at.isoformat() if brief.approved_at else None,
        "created_at": brief.created_at.isoformat(),
        "updated_at": brief.updated_at.isoformat(),
    }


@router.post("/{campaign_id}/briefs/{brief_id}/approve", response=BriefResponseSchema)
def approve_brief(
    request,
    campaign_id: int,
    brief_id: int,
    payload: BriefApproveSchema,
) -> dict[str, Any]:
    """Approve or reject a brief.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.
        brief_id: Brief ID.
        payload: Approval payload.

    Returns:
        Updated brief.
    """
    brief = get_object_or_404(CampaignBrief, id=brief_id, campaign_id=campaign_id)
    brief.is_approved = payload.approved
    if payload.approved:
        brief.approved_by = getattr(request, "user_id", "")
        brief.approved_at = datetime.now(timezone.utc)
        # Also update the campaign brief_approved flag
        campaign = get_object_or_404(Campaign, id=campaign_id)
        campaign.brief_approved = True
        campaign.save(update_fields=["brief_approved", "updated_at"])
    brief.save(update_fields=["is_approved", "approved_by", "approved_at", "updated_at"])
    return brief
