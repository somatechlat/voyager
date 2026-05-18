"""Budget management service with pacing algorithms.

Implements even, accelerated, front-loaded, and performance-based
budget pacing algorithms with alert thresholds.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from apps.campaigns.models import Campaign, CampaignBudget, CampaignChannel

logger = logging.getLogger(__name__)

# Budget alert thresholds as percentages
ALERT_THRESHOLDS = [50, 75, 90, 100]


def calculate_pacing(campaign: Campaign) -> dict[str, Any]:
    """Calculate daily budget using the campaign's pacing algorithm.

    Supports even, accelerated, front-loaded, and performance-based pacing.

    Args:
        campaign: The campaign to calculate pacing for.

    Returns:
        Dict with daily_budget, pacing_type, days_remaining, and reasoning.
    """
    if not campaign.budget or campaign.budget <= 0:
        return {"daily_budget": 0.0, "pacing_type": campaign.pacing_type, "days_remaining": 0}

    days_remaining = campaign.days_remaining
    days_elapsed = campaign.days_elapsed

    if days_remaining is None or days_elapsed is None:
        return {"daily_budget": 0.0, "pacing_type": campaign.pacing_type, "days_remaining": 0}

    total_days = days_elapsed + days_remaining
    if total_days <= 0:
        return {"daily_budget": 0.0, "pacing_type": campaign.pacing_type, "days_remaining": 0}

    spent = float(campaign.current_spend)
    total = float(campaign.budget)
    remaining = total - spent

    if remaining <= 0:
        return {"daily_budget": 0.0, "pacing_type": campaign.pacing_type, "days_remaining": 0}

    if campaign.pacing_type == Campaign.PacingType.EVEN:
        daily = remaining / days_remaining
        return {
            "daily_budget": round(daily, 2),
            "pacing_type": campaign.pacing_type,
            "days_remaining": days_remaining,
            "reasoning": f"Even split: {remaining:.2f} / {days_remaining} days",
        }

    if campaign.pacing_type == Campaign.PacingType.ACCELERATED:
        # Spend more early, taper off
        remaining_fraction = days_remaining / total_days if total_days > 0 else 0
        if remaining_fraction > 0:
            daily = remaining * (2.0 * remaining_fraction) / days_remaining
        else:
            daily = remaining / max(1, days_remaining)
        return {
            "daily_budget": round(daily, 2),
            "pacing_type": campaign.pacing_type,
            "days_remaining": days_remaining,
            "reasoning": f"Accelerated: weight={2.0 * remaining_fraction:.2f}",
        }

    if campaign.pacing_type == Campaign.PacingType.FRONT_LOADED:
        # 60% in first 40% of campaign
        elapsed_fraction = days_elapsed / total_days if total_days > 0 else 0
        if elapsed_fraction < 0.4:
            phase_budget = total * 0.6 - spent
            phase_days = total_days * 0.4 - days_elapsed
            daily = phase_budget / max(1, phase_days) if phase_days > 0 else remaining
        else:
            phase_spent_target = total * 0.6
            phase_remaining_budget = total * 0.4 - max(0, spent - phase_spent_target)
            daily = phase_remaining_budget / max(1, days_remaining)
        return {
            "daily_budget": round(daily, 2),
            "pacing_type": campaign.pacing_type,
            "days_remaining": days_remaining,
            "reasoning": f"Front-loaded: elapsed={elapsed_fraction:.1%}",
        }

    if campaign.pacing_type == Campaign.PacingType.PERFORMANCE:
        return _calculate_performance_pacing(campaign, remaining, days_remaining)

    return {"daily_budget": round(remaining / max(1, days_remaining), 2),
            "pacing_type": campaign.pacing_type,
            "days_remaining": days_remaining}


def _calculate_performance_pacing(
    campaign: Campaign,
    remaining_budget: float,
    days_remaining: int,
) -> dict[str, Any]:
    """Allocate budget based on channel ROAS performance.

    Higher-performing channels get larger budget allocations.

    Args:
        campaign: The campaign.
        remaining_budget: Remaining budget amount.
        days_remaining: Days remaining in campaign.

    Returns:
        Pacing result with per-channel breakdown.
    """
    channels = list(campaign.channel_configs.all())
    if not channels:
        daily = remaining_budget / max(1, days_remaining)
        return {
            "daily_budget": round(daily, 2),
            "pacing_type": campaign.pacing_type,
            "days_remaining": days_remaining,
            "reasoning": "No channels configured, using even split",
            "channel_breakdown": [],
        }

    # Calculate weights based on ROAS
    total_roas = 0.0
    channel_data: list[dict[str, Any]] = []
    for ch in channels:
        roas = ch.roas if ch.roas > 0 else 0.1  # Minimum weight
        total_roas += roas
        channel_data.append({"channel": ch, "roas": roas})

    if total_roas <= 0:
        total_roas = len(channel_data) * 0.1

    daily_total = remaining_budget / max(1, days_remaining)
    breakdown: list[dict[str, Any]] = []

    for cd in channel_data:
        weight = cd["roas"] / total_roas
        ch_daily = daily_total * weight
        breakdown.append(
            {
                "channel_id": cd["channel"].id,
                "channel_type": cd["channel"].channel_type,
                "platform": cd["channel"].platform,
                "roas": cd["roas"],
                "weight": round(weight, 4),
                "daily_budget": round(ch_daily, 2),
            }
        )

    return {
        "daily_budget": round(daily_total, 2),
        "pacing_type": campaign.pacing_type,
        "days_remaining": days_remaining,
        "reasoning": f"Performance-weighted across {len(channels)} channels",
        "channel_breakdown": breakdown,
    }


def check_budget_alerts(campaign: Campaign) -> list[dict[str, Any]]:
    """Check campaign spend against budget alert thresholds.

    Evaluates 50%, 75%, 90%, and 100% thresholds plus
    forecasted overspend based on current burn rate.

    Args:
        campaign: The campaign to check.

    Returns:
        List of alert dicts with level, message, severity.
    """
    alerts: list[dict[str, Any]] = []
    if not campaign.budget or campaign.budget <= 0:
        return alerts

    spend_pct = campaign.spend_percentage
    alerts_sent = campaign.alerts_sent if isinstance(campaign.alerts_sent, dict) else {}

    for threshold in ALERT_THRESHOLDS:
        threshold_key = str(threshold)
        if spend_pct >= threshold and not alerts_sent.get(threshold_key):
            if threshold >= 90:
                severity = "critical"
            elif threshold >= 75:
                severity = "warning"
            else:
                severity = "info"

            alerts.append(
                {
                    "level": threshold,
                    "message": (
                        f'Campaign "{campaign.name}" has spent '
                        f"{spend_pct:.1f}% of budget"
                    ),
                    "severity": severity,
                }
            )
            alerts_sent[threshold_key] = date.today().isoformat()

    # Forecasted overspend
    days_elapsed = campaign.days_elapsed
    if days_elapsed and days_elapsed > 0 and campaign.start_date and campaign.end_date:
        total_days = (campaign.end_date - campaign.start_date).days
        if total_days > 0:
            daily_burn = float(campaign.current_spend) / days_elapsed
            forecasted_total = daily_burn * total_days
            if forecasted_total > float(campaign.budget) * 1.1:
                over_pct = (forecasted_total / float(campaign.budget) - 1.0) * 100.0
                alerts.append(
                    {
                        "level": "forecast",
                        "message": (
                            f'At current pace, campaign "{campaign.name}" '
                            f"will exceed budget by {over_pct:.0f}%"
                        ),
                        "severity": "critical",
                    }
                )

    # Persist alerts sent
    if alerts:
        campaign.alerts_sent = alerts_sent
        campaign.save(update_fields=["alerts_sent", "updated_at"])

    return alerts


def record_spend(
    campaign: Campaign,
    amount: float,
    channel: str = "",
    description: str = "",
    metadata: dict[str, Any] | None = None,
) -> CampaignBudget:
    """Record a spend transaction on a campaign.

    Creates a CampaignBudget entry and updates campaign.current_spend.

    Args:
        campaign: The campaign.
        amount: Amount spent (positive number).
        channel: Channel identifier.
        description: Transaction description.
        metadata: Additional metadata.

    Returns:
        The created CampaignBudget record.
    """
    entry = CampaignBudget.objects.create(
        campaign=campaign,
        amount=-abs(amount),
        type=CampaignBudget.EntryType.SPEND,
        channel=channel,
        description=description,
        metadata=metadata or {},
    )

    campaign.current_spend = float(campaign.current_spend) + abs(amount)
    campaign.save(update_fields=["current_spend", "updated_at"])

    return entry


def record_allocation(
    campaign: Campaign,
    amount: float,
    description: str = "",
) -> CampaignBudget:
    """Record a budget allocation for a campaign.

    Args:
        campaign: The campaign.
        amount: Amount allocated (positive).
        description: Transaction description.

    Returns:
        The created CampaignBudget record.
    """
    entry = CampaignBudget.objects.create(
        campaign=campaign,
        amount=abs(amount),
        type=CampaignBudget.EntryType.ALLOCATION,
        description=description,
    )

    if campaign.budget is None:
        campaign.budget = 0
    campaign.budget = float(campaign.budget) + abs(amount)
    campaign.save(update_fields=["budget", "updated_at"])

    return entry
