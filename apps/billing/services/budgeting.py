"""Budgeting service.

Handles budget consumption tracking, alert threshold evaluation,
forecasting, and reporting.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from apps.billing.models.project_budget import ProjectBudget


DEFAULT_ALERT_THRESHOLDS: dict[str, list[float]] = {
    "fixed": [50.0, 75.0, 90.0, 100.0],
    "hourly": [75.0, 90.0, 100.0],
    "retainer": [75.0, 90.0, 100.0],
    "hybrid": [75.0, 90.0, 100.0],
}


def get_alert_level(consumption_pct: float, thresholds: list[float]) -> str:
    """Determine alert level from consumption percentage.

    Args:
        consumption_pct: Percentage consumed (0-100+).
        thresholds: List of threshold percentages.

    Returns:
        Alert level string: none, low, medium, high, critical.
    """
    if consumption_pct >= 100:
        return "critical"
    if consumption_pct >= 90:
        return "high"
    if consumption_pct >= 75:
        return "medium"
    if consumption_pct >= 50:
        return "low"
    return "none"


def evaluate_budget_alert(budget: ProjectBudget) -> dict[str, Any]:
    """Evaluate alert status for a budget.

    Args:
        budget: The project budget to evaluate.

    Returns:
        Dict with alert_level, consumption_pct, and triggered.
    """
    if budget.total_budget and budget.total_budget > 0:
        consumption_pct = float(
            (budget.budget_consumed / budget.total_budget) * 100
        )
    else:
        consumption_pct = 0.0
    custom = budget.alert_thresholds or {}
    thresholds = custom.get(
        "thresholds", DEFAULT_ALERT_THRESHOLDS.get(budget.budget_type, [75.0, 90.0, 100.0])
    )
    level = get_alert_level(consumption_pct, thresholds)
    triggered = level != "none" and (
        budget.alert_level == ProjectBudget.AlertLevel.NONE
        or _level_rank(level) > _level_rank(budget.alert_level)
    )
    return {
        "alert_level": level,
        "consumption_pct": round(consumption_pct, 2),
        "thresholds": thresholds,
        "triggered": triggered,
        "budget_id": budget.pk,
    }


def _level_rank(level: str) -> int:
    """Return numeric rank for an alert level."""
    ranks = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    return ranks.get(level, 0)


def update_budget_consumption(
    budget: ProjectBudget, amount: Decimal, hours: Decimal = Decimal("0")
) -> dict[str, Any]:
    """Add consumption to a budget and re-evaluate alerts.

    Args:
        budget: The project budget.
        amount: Amount to add to consumption.
        hours: Hours to add (optional).

    Returns:
        Dict with updated consumption and alert status.
    """
    budget.budget_consumed += amount
    budget.hours_consumed += hours
    alert = evaluate_budget_alert(budget)
    budget.alert_level = alert["alert_level"]
    if alert["triggered"]:
        budget.last_alert_sent_at = datetime_now()
    budget.save()
    return {
        "budget_consumed": str(budget.budget_consumed),
        "hours_consumed": str(budget.hours_consumed),
        "alert": alert,
    }


def datetime_now():
    """Return current UTC datetime."""
    from django.utils import timezone

    return timezone.now()


def forecast_budget(budget: ProjectBudget) -> dict[str, Any]:
    """Forecast budget completion based on burn rate.

    Args:
        budget: The project budget to forecast.

    Returns:
        Dict with forecast metrics.
    """
    today = date.today()
    days_elapsed = (today - budget.start_date).days or 1
    daily_burn = float(budget.budget_consumed) / days_elapsed
    remaining = float(budget.total_budget) - float(budget.budget_consumed)
    est_days_remaining = remaining / daily_burn if daily_burn > 0 else 0
    est_completion = today + timedelta(days=int(est_days_remaining))
    planned_end = budget.end_date or today
    days_over = (est_completion - planned_end).days
    consumption_pct = (
        (float(budget.budget_consumed) / float(budget.total_budget) * 100)
        if budget.total_budget > 0
        else 0
    )
    return {
        "budget_total": str(budget.total_budget),
        "budget_consumed": str(budget.budget_consumed),
        "budget_remaining": str(remaining),
        "consumption_pct": round(consumption_pct, 2),
        "daily_burn_rate": round(daily_burn, 2),
        "estimated_completion_date": str(est_completion),
        "days_over_under": days_over,
        "on_budget": est_completion <= planned_end,
        "projected_overrun": round(daily_burn * days_over, 2) if days_over > 0 else 0,
    }
