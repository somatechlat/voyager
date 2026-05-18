"""Retainer management service.

Handles retainer lifecycle, auto-renewal, consumption tracking,
rollover calculation, and overage billing.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from apps.billing.models.retainer import Retainer
from apps.billing.models.time_entry import TimeEntry


def get_month_start_end(d: date) -> tuple[date, date]:
    """Return start and end dates for a month.

    Args:
        d: A date within the month.

    Returns:
        Tuple of (month_start, month_end).
    """
    start = date(d.year, d.month, 1)
    end_day = monthrange(d.year, d.month)[1]
    end = date(d.year, d.month, end_day)
    return start, end


def calculate_monthly_usage(retainer: Retainer, month: date) -> dict[str, Any]:
    """Calculate hours used for a retainer in a given month.

    Args:
        retainer: The retainer agreement.
        month: A date within the billing month.

    Returns:
        Dict with hours_billed, hours_remaining, consumption_pct.
    """
    month_start, month_end = get_month_start_end(month)
    entries = TimeEntry.objects.filter(
        tenant_id=retainer.tenant_id,
        client=retainer.client_id,
        started_at__date__gte=month_start,
        started_at__date__lte=month_end,
        status__in=[TimeEntry.Status.APPROVED, TimeEntry.Status.INVOICED],
        is_billable=True,
    )
    total_minutes = sum(e.rounded_minutes for e in entries)
    hours_billed = Decimal(str(total_minutes)) / Decimal("60")
    monthly_hours = retainer.monthly_hours or Decimal("0")
    remaining = monthly_hours - hours_billed if monthly_hours else Decimal("0")
    consumption_pct = (
        Decimal(str(round((hours_billed / monthly_hours) * 100, 2)))
        if monthly_hours > 0
        else Decimal("0")
    )
    return {
        "hours_billed": round(hours_billed, 2),
        "hours_remaining": round(remaining, 2),
        "consumption_pct": consumption_pct,
        "month": month.strftime("%Y-%m"),
    }


def calculate_rollover(retainer: Retainer, month: date) -> dict[str, Any]:
    """Calculate rollover hours for unused retainer allocation.

    Args:
        retainer: The retainer agreement.
        month: The billing month.

    Returns:
        Dict with rollover_hours, forfeited_hours, overage_hours.
    """
    usage = calculate_monthly_usage(retainer, month)
    monthly_hours = retainer.monthly_hours or Decimal("0")
    unused_hours = monthly_hours - Decimal(str(usage["hours_billed"]))
    if unused_hours <= 0:
        return {
            "rollover_hours": Decimal("0"),
            "forfeited_hours": Decimal("0"),
            "overage_hours": abs(unused_hours),
        }
    policy = retainer.rollover_policy or {}
    max_rollover = Decimal(str(policy.get("maxRolloverHours", 0)))
    rollover_hours = min(unused_hours, max_rollover)
    forfeited_hours = unused_hours - rollover_hours
    return {
        "rollover_hours": rollover_hours,
        "forfeited_hours": forfeited_hours,
        "overage_hours": Decimal("0"),
    }


def check_consumption_alerts(retainer: Retainer, month: date) -> list[dict[str, Any]]:
    """Check if consumption thresholds are exceeded.

    Args:
        retainer: The retainer agreement.
        month: The billing month.

    Returns:
        List of triggered alerts.
    """
    usage = calculate_monthly_usage(retainer, month)
    thresholds = retainer.consumption_alert_thresholds or [75, 90, 100]
    alerts = []
    for threshold in sorted(thresholds):
        if usage["consumption_pct"] >= threshold:
            alerts.append(
                {
                    "threshold": threshold,
                    "current_pct": str(usage["consumption_pct"]),
                    "message": (
                        f"Retainer {retainer.name} has consumed "
                        f"{usage['consumption_pct']}% of monthly allocation"
                    ),
                    "severity": (
                        "critical" if threshold >= 100 else "warning" if threshold >= 90 else "info"
                    ),
                }
            )
    return alerts


def should_auto_renew(retainer: Retainer) -> bool:
    """Determine if retainer should auto-renew.

    Args:
        retainer: The retainer to evaluate.

    Returns:
        True if the retainer should be renewed.
    """
    if retainer.status != Retainer.Status.ACTIVE:
        return False
    if retainer.renewal_type == Retainer.RenewalType.MANUAL:
        return False
    if not retainer.end_date:
        return False
    days_until = (retainer.end_date - date.today()).days
    return days_until <= 30


def renew_retainer(retainer: Retainer) -> dict[str, Any]:
    """Renew a retainer for another term.

    Args:
        retainer: The retainer to renew.

    Returns:
        Dict with renewal result.
    """
    if retainer.end_date:
        retainer.end_date = retainer.end_date + timedelta(days=retainer.renewal_term_months * 30)
    retainer.status = Retainer.Status.ACTIVE
    retainer.save(update_fields=["end_date", "status", "updated_at"])
    return {
        "retainer_id": retainer.pk,
        "new_end_date": str(retainer.end_date),
        "status": retainer.status,
        "renewed_at": datetime.now().isoformat(),
    }
