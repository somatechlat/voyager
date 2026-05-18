"""Multi-channel campaign orchestration service.

Manages channel dependencies, critical path calculation, and
launch sequencing across 8 marketing channel types.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import date, timedelta
from typing import Any

from apps.campaigns.models import Campaign, CampaignChannel

logger = logging.getLogger(__name__)


def build_dependency_graph(
    channels: list[CampaignChannel],
) -> dict[int, list[int]]:
    """Build a dependency graph from channel dependencies.

    Args:
        channels: List of campaign channels.

    Returns:
        Dict mapping channel ID to list of dependent channel IDs.
    """
    graph: dict[int, list[int]] = {ch.id: [] for ch in channels}
    dep_map: dict[str, int] = {
        f"{ch.channel_type}:{ch.platform}": ch.id for ch in channels
    }

    for ch in channels:
        for dep in ch.dependencies:
            dep_key = dep if isinstance(dep, str) else dep.get("ref", "")
            if dep_key in dep_map:
                dep_id = dep_map[dep_key]
                if ch.id not in graph[dep_id]:
                    graph[dep_id].append(ch.id)
    return graph


def has_cycle(graph: dict[int, list[int]]) -> bool:
    """Detect cycles in the dependency graph using DFS.

    Args:
        graph: Dependency graph mapping node -> dependents.

    Returns:
        True if a cycle is detected.
    """
    visited: set[int] = set()
    rec_stack: set[int] = set()

    def _dfs(node: int) -> bool:
        visited.add(node)
        rec_stack.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if _dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        rec_stack.remove(node)
        return False

    for node in list(graph.keys()):
        if node not in visited:
            if _dfs(node):
                return True
    return False


def topological_sort(graph: dict[int, list[int]]) -> list[int]:
    """Return channels in topological order (dependencies first).

    Args:
        graph: Dependency graph mapping node -> dependents.

    Returns:
        List of channel IDs in execution order.
    """
    in_degree: dict[int, int] = {node: 0 for node in graph}
    for node in graph:
        for dep in graph[node]:
            in_degree[dep] = in_degree.get(dep, 0) + 1

    queue = deque([n for n, d in in_degree.items() if d == 0])
    result: list[int] = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for dep in graph.get(node, []):
            in_degree[dep] = in_degree[dep] - 1
            if in_degree[dep] == 0:
                queue.append(dep)

    return result


def find_critical_path(
    channels: list[CampaignChannel],
    graph: dict[int, list[int]],
) -> dict[str, Any]:
    """Find the critical path through the channel dependency graph.

    Args:
        channels: List of campaign channels.
        graph: Dependency graph.

    Returns:
        Dict with critical_channel_ids, total_duration_days.
    """
    ch_map: dict[int, CampaignChannel] = {ch.id: ch for ch in channels}
    topo = topological_sort(graph)

    # Duration = lead_time + (end_date - start_date if set, else 7 days default)
    durations: dict[int, int] = {}
    for ch in channels:
        if ch.start_date and ch.end_date:
            durations[ch.id] = max(1, (ch.end_date - ch.start_date).days)
        else:
            durations[ch.id] = max(1, ch.lead_time_days + 7)

    # Earliest start / finish
    earliest_start: dict[int, int] = {ch.id: 0 for ch in channels}
    earliest_finish: dict[int, int] = {}

    for node in topo:
        duration = durations.get(node, 1)
        earliest_finish[node] = earliest_start[node] + duration
        for dep in graph.get(node, []):
            earliest_start[dep] = max(
                earliest_start.get(dep, 0), earliest_finish[node]
            )

    if not earliest_finish:
        return {"critical_channel_ids": [], "total_duration_days": 0}

    # Find the longest path (critical path)
    max_finish = max(earliest_finish.values())
    critical_end = next(
        nid for nid, fin in earliest_finish.items() if fin == max_finish
    )

    # Backtrack to find the critical path
    critical_path: list[int] = []
    current = critical_end
    reverse_deps: dict[int, list[int]] = {ch.id: [] for ch in channels}
    for node, deps in graph.items():
        for dep in deps:
            reverse_deps.setdefault(dep, []).append(node)

    # Simple approach: find nodes on the longest path
    # Backtrack from the end node following reverse dependencies
    visited_nodes: set[int] = set()
    stack = [critical_end]
    while stack:
        node = stack.pop()
        if node in visited_nodes:
            continue
        visited_nodes.add(node)
        critical_path.append(node)
        preds = [n for n, deps in graph.items() if node in deps]
        if preds:
            # Pick the predecessor with latest finish
            pred = max(preds, key=lambda p: earliest_finish.get(p, 0))
            stack.append(pred)

    critical_path.reverse()
    return {
        "critical_channel_ids": critical_path,
        "total_duration_days": max_finish,
    }


def schedule_channels(
    campaign: Campaign,
    channels: list[CampaignChannel],
) -> list[dict[str, Any]]:
    """Schedule channel launch dates based on dependencies and lead times.

    Args:
        campaign: The parent campaign.
        channels: List of channels to schedule.

    Returns:
        List of scheduling info dicts per channel.
    """
    graph = build_dependency_graph(channels)

    if has_cycle(graph):
        raise ValueError("Circular dependency detected between channels")

    topo = topological_sort(graph)
    ch_map: dict[int, CampaignChannel] = {ch.id: ch for ch in channels}
    scheduled: list[dict[str, Any]] = []

    campaign_start = campaign.start_date or date.today()
    earliest_finishes: dict[int, date] = {}

    for ch_id in topo:
        ch = ch_map.get(ch_id)
        if not ch:
            continue

        # Find the latest finish among dependencies
        dep_latest: date | None = None
        for dep_node, dep_list in graph.items():
            if ch_id in dep_list:
                dep_finish = earliest_finishes.get(dep_node)
                if dep_finish and (dep_latest is None or dep_finish > dep_latest):
                    dep_latest = dep_finish

        if dep_latest:
            ch_start = dep_latest + timedelta(days=ch.lead_time_days)
        else:
            ch_start = campaign_start

        # Default duration: 7 days if not set
        if ch.start_date and ch.end_date:
            duration_days = max(1, (ch.end_date - ch.start_date).days)
        else:
            duration_days = 7

        ch_end = ch_start + timedelta(days=duration_days)
        earliest_finishes[ch_id] = ch_end

        scheduled.append(
            {
                "channel_id": ch.id,
                "channel_type": ch.channel_type,
                "platform": ch.platform,
                "scheduled_start": ch_start.isoformat(),
                "scheduled_end": ch_end.isoformat(),
                "lead_time_days": ch.lead_time_days,
                "depends_on": [
                    dep_node
                    for dep_node, dep_list in graph.items()
                    if ch_id in dep_list
                ],
            }
        )

    return scheduled


def get_channel_recommendations(
    objective: str,
    audience_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Score and recommend channels based on objective and audience.

    Uses the scoring formula:
    score = (audienceOverlap * 0.4) + (historicalPerformance * 0.3)
            + (costEfficiency * 0.3)

    Args:
        objective: Campaign objective (awareness, engagement, conversion, retention).
        audience_data: Optional audience presence data per channel.

    Returns:
        List of channel recommendations sorted by score descending.
    """
    channel_profiles: list[dict[str, Any]] = [
        {
            "channel_type": CampaignChannel.ChannelType.ORGANIC_SOCIAL,
            "audience_overlap": 0.85,
            "historical_performance": 0.70,
            "cost_efficiency": 0.90,
            "objective_fit": {"awareness": 0.9, "engagement": 0.9, "conversion": 0.5, "retention": 0.7},
        },
        {
            "channel_type": CampaignChannel.ChannelType.PAID_SEARCH,
            "audience_overlap": 0.75,
            "historical_performance": 0.85,
            "cost_efficiency": 0.60,
            "objective_fit": {"awareness": 0.6, "engagement": 0.5, "conversion": 0.95, "retention": 0.4},
        },
        {
            "channel_type": CampaignChannel.ChannelType.PAID_SOCIAL,
            "audience_overlap": 0.90,
            "historical_performance": 0.80,
            "cost_efficiency": 0.65,
            "objective_fit": {"awareness": 0.9, "engagement": 0.85, "conversion": 0.8, "retention": 0.7},
        },
        {
            "channel_type": CampaignChannel.ChannelType.EMAIL,
            "audience_overlap": 0.70,
            "historical_performance": 0.90,
            "cost_efficiency": 0.95,
            "objective_fit": {"awareness": 0.4, "engagement": 0.7, "conversion": 0.85, "retention": 0.95},
        },
        {
            "channel_type": CampaignChannel.ChannelType.SEO,
            "audience_overlap": 0.80,
            "historical_performance": 0.75,
            "cost_efficiency": 0.95,
            "objective_fit": {"awareness": 0.8, "engagement": 0.7, "conversion": 0.7, "retention": 0.5},
        },
        {
            "channel_type": CampaignChannel.ChannelType.INFLUENCER,
            "audience_overlap": 0.65,
            "historical_performance": 0.75,
            "cost_efficiency": 0.50,
            "objective_fit": {"awareness": 0.95, "engagement": 0.9, "conversion": 0.6, "retention": 0.5},
        },
        {
            "channel_type": CampaignChannel.ChannelType.DISPLAY,
            "audience_overlap": 0.85,
            "historical_performance": 0.60,
            "cost_efficiency": 0.80,
            "objective_fit": {"awareness": 0.9, "engagement": 0.6, "conversion": 0.6, "retention": 0.5},
        },
        {
            "channel_type": CampaignChannel.ChannelType.VIDEO,
            "audience_overlap": 0.88,
            "historical_performance": 0.82,
            "cost_efficiency": 0.55,
            "objective_fit": {"awareness": 0.95, "engagement": 0.9, "conversion": 0.7, "retention": 0.6},
        },
    ]

    scored: list[dict[str, Any]] = []
    for profile in channel_profiles:
        obj_fit = profile["objective_fit"].get(objective, 0.5)
        audience = profile["audience_overlap"]
        perf = profile["historical_performance"]
        cost = profile["cost_efficiency"]
        score = (audience * 0.4) + (perf * 0.3) + (cost * 0.3)
        adjusted_score = score * obj_fit

        scored.append(
            {
                "channel_type": profile["channel_type"],
                "score": round(adjusted_score, 4),
                "objective_fit": obj_fit,
                "audience_overlap": audience,
                "historical_performance": perf,
                "cost_efficiency": cost,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored
