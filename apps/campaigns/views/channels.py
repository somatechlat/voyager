"""Campaign channel orchestration views.

Dependency graph, scheduling, critical path, and recommendations.
"""

from __future__ import annotations

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router

from apps.campaigns.models import Campaign
from apps.campaigns.serializers import ChannelScheduleSchema
from apps.campaigns.services.channels import (
    find_critical_path,
    get_channel_recommendations,
    schedule_channels,
)

logger = logging.getLogger(__name__)

router = Router()


@router.get("/{campaign_id}/channels/schedule", response=list[ChannelScheduleSchema])
def get_schedule(
    request,
    campaign_id: int,
) -> list[dict[str, Any]]:
    """Get scheduled launch dates for all channels.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        List of scheduled channel entries.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    channels = list(campaign.channel_configs.all())
    if not channels:
        return []
    return schedule_channels(campaign, channels)


@router.get("/{campaign_id}/channels/critical-path")
def get_critical_path(
    request,
    campaign_id: int,
) -> dict[str, Any]:
    """Get the critical path through channel dependencies.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Critical path dict.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    channels = list(campaign.channel_configs.all())
    if not channels:
        return {"critical_channel_ids": [], "total_duration_days": 0}

    from apps.campaigns.services.channels import build_dependency_graph

    graph = build_dependency_graph(channels)
    result = find_critical_path(channels, graph)

    # Map IDs to channel info
    ch_map = {ch.id: ch for ch in channels}
    path_info = [
        {
            "id": ch_id,
            "channel_type": ch_map[ch_id].channel_type if ch_id in ch_map else "unknown",
            "platform": ch_map[ch_id].platform if ch_id in ch_map else "unknown",
        }
        for ch_id in result["critical_channel_ids"]
    ]

    return {
        **result,
        "path": path_info,
    }


@router.get("/{campaign_id}/channels/recommendations")
def channel_recommendations(
    request,
    campaign_id: int,
) -> list[dict[str, Any]]:
    """Get channel recommendations for a campaign.

    Args:
        request: HTTP request.
        campaign_id: Campaign ID.

    Returns:
        Scored channel recommendations.
    """
    campaign = get_object_or_404(Campaign, id=campaign_id)
    return get_channel_recommendations(
        objective=campaign.objective,
        audience_data=campaign.target_audience,
    )
