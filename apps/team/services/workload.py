"""Workload service — utilization calculation and capacity planning.

Provides team capacity analysis, overload detection, and rebalancing
suggestions based on task assignments and estimated hours.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum

from apps.team.models import Task

logger = logging.getLogger(__name__)

DEFAULT_WEEKLY_CAPACITY = 40
MEETING_HOURS_DEFAULT = 8
RECURRING_HOURS_DEFAULT = 5
OVERLOAD_THRESHOLD = 1.0
AT_RISK_THRESHOLD = 0.85


class WorkloadServiceError(Exception):
    """Raised when a workload operation fails."""

    pass


class WorkloadService:
    """Service layer for workload balancing and capacity planning."""

    # -- Utilization calculations ------------------------------------------

    @staticmethod
    def get_user_workload(
        tenant_id: str, user_id: str, date_from: date | None = None, date_to: date | None = None
    ) -> dict[str, Any]:
        """Calculate workload metrics for a single user.

        Args:
            tenant_id: Tenant scope identifier.
            user_id: User to analyze.
            date_from: Start date for task filter.
            date_to: End date for task filter.

        Returns:
            Dict with assigned counts, hours, overdue count, etc.
        """
        qs = Task.objects.filter(tenant_id=tenant_id, assignee_id=user_id)
        qs = qs.exclude(status__in=["done", "cancelled"])

        if date_from:
            qs = qs.filter(due_date__gte=date_from)
        if date_to:
            qs = qs.filter(due_date__lte=date_to)

        by_status = dict(
            qs.values("status").annotate(count=Count("id")).values_list("status", "count")
        )
        by_priority = dict(
            qs.values("priority")
            .annotate(count=Count("id"))
            .values_list("priority", "count")
        )

        total_assigned = qs.count()

        overdue_count = qs.filter(due_date__lt=date.today()).count()

        hours_agg = qs.aggregate(
            total_estimated=Sum("estimated_hours"),
            total_actual=Sum("actual_hours"),
        )

        upcoming = (
            qs.filter(due_date__gte=date.today())
            .exclude(status="done")
            .order_by("due_date")[:10]
        )
        upcoming_list = [
            {
                "task_id": t.id,
                "title": t.title,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "priority": t.priority,
                "estimated_hours": str(t.estimated_hours) if t.estimated_hours else "0",
            }
            for t in upcoming
        ]

        return {
            "user_id": user_id,
            "total_assigned": total_assigned,
            "by_status": by_status,
            "by_priority": by_priority,
            "overdue_count": overdue_count,
            "total_estimated_hours": hours_agg["total_estimated"] or Decimal("0"),
            "total_actual_hours": hours_agg["total_actual"] or Decimal("0"),
            "upcoming_due_dates": upcoming_list,
        }

    @staticmethod
    def get_team_workload(
        tenant_id: str,
        user_ids: list[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        """Calculate workload for the entire team or specified users.

        Args:
            tenant_id: Tenant scope identifier.
            user_ids: Optional list of user IDs. If None, all assignees.
            date_from: Start date for task filter.
            date_to: End date for task filter.

        Returns:
            Dict with per-user workloads and team totals.
        """
        if user_ids is None:
            user_ids = list(
                Task.objects.filter(tenant_id=tenant_id)
                .exclude(assignee_id="")
                .values_list("assignee_id", flat=True)
                .distinct()
            )

        workloads = []
        for uid in user_ids:
            try:
                wl = WorkloadService.get_user_workload(
                    tenant_id, uid, date_from, date_to
                )
                workloads.append(wl)
            except Exception:
                logger.warning("Failed to get workload for user %s", uid)
                continue

        team_totals = {
            "total_assigned": sum(w["total_assigned"] for w in workloads),
            "total_overdue": sum(w["overdue_count"] for w in workloads),
            "total_estimated_hours": sum(
                w["total_estimated_hours"] for w in workloads
            ),
            "total_actual_hours": sum(w["total_actual_hours"] for w in workloads),
            "member_count": len(workloads),
        }

        return {
            "tenant_id": tenant_id,
            "user_workloads": workloads,
            "team_totals": team_totals,
        }

    # -- Capacity planning -------------------------------------------------

    @staticmethod
    def check_capacity(
        tenant_id: str,
        user_ids: list[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        weekly_capacity: int = DEFAULT_WEEKLY_CAPACITY,
        meeting_hours: int = MEETING_HOURS_DEFAULT,
        recurring_hours: int = RECURRING_HOURS_DEFAULT,
    ) -> dict[str, Any]:
        """Analyze team capacity and detect overload.

        Args:
            tenant_id: Tenant scope identifier.
            user_ids: Optional list of user IDs to analyze.
            date_from: Start date for task filter.
            date_to: End date for task filter.
            weekly_capacity: Hours per week per user.
            meeting_hours: Hours reserved for meetings.
            recurring_hours: Hours reserved for recurring tasks.

        Returns:
            Dict with per-user capacities, overload/risk lists, and suggestions.
        """
        if date_from is None:
            date_from = date.today()
        if date_to is None:
            date_to = date_from + timedelta(days=7)

        if user_ids is None:
            user_ids = list(
                Task.objects.filter(tenant_id=tenant_id)
                .exclude(assignee_id="")
                .values_list("assignee_id", flat=True)
                .distinct()
            )

        available_hours = weekly_capacity - meeting_hours - recurring_hours
        if available_hours < 1:
            available_hours = 1

        capacities: list[dict[str, Any]] = []
        overloaded: list[dict[str, Any]] = []
        at_risk: list[dict[str, Any]] = []
        underutilized: list[dict[str, Any]] = []

        for uid in user_ids:
            qs = Task.objects.filter(
                tenant_id=tenant_id, assignee_id=uid
            ).exclude(status__in=["done", "cancelled"])

            if date_from:
                qs = qs.filter(due_date__gte=date_from)
            if date_to:
                qs = qs.filter(due_date__lte=date_to)

            assigned_tasks = qs.count()
            estimated_hours = (
                qs.aggregate(total=Sum("estimated_hours"))["total"] or Decimal("0")
            )

            utilization = (
                float(estimated_hours) / available_hours if available_hours > 0 else 0.0
            )

            if utilization > OVERLOAD_THRESHOLD:
                status = "overloaded"
                overage = float(estimated_hours) - available_hours
                suggestion = f"Redistribute {overage:.1f}h of work from this user"
                overloaded.append(
                    {
                        "user_id": uid,
                        "assigned_tasks": assigned_tasks,
                        "estimated_hours": estimated_hours,
                        "available_hours": Decimal(available_hours),
                        "utilization_rate": round(utilization, 2),
                        "status": status,
                        "suggestion": suggestion,
                    }
                )
            elif utilization > AT_RISK_THRESHOLD:
                status = "at_risk"
                suggestion = "Approaching capacity limit"
                at_risk.append(
                    {
                        "user_id": uid,
                        "assigned_tasks": assigned_tasks,
                        "estimated_hours": estimated_hours,
                        "available_hours": Decimal(available_hours),
                        "utilization_rate": round(utilization, 2),
                        "status": status,
                        "suggestion": suggestion,
                    }
                )
            else:
                status = "normal"
                suggestion = ""
                underutilized.append(
                    {
                        "user_id": uid,
                        "assigned_tasks": assigned_tasks,
                        "estimated_hours": estimated_hours,
                        "available_hours": Decimal(available_hours),
                        "utilization_rate": round(utilization, 2),
                        "status": status,
                        "suggestion": suggestion,
                    }
                )

            capacities.append(
                {
                    "user_id": uid,
                    "assigned_tasks": assigned_tasks,
                    "estimated_hours": estimated_hours,
                    "available_hours": Decimal(available_hours),
                    "utilization_rate": round(utilization, 2),
                    "status": status,
                    "suggestion": suggestion,
                }
            )

        suggestions = WorkloadService._generate_suggestions(
            overloaded, underutilized, tenant_id, date_from, date_to
        )

        return {
            "tenant_id": tenant_id,
            "date_from": date_from,
            "date_to": date_to,
            "user_capacities": capacities,
            "overloaded": overloaded,
            "at_risk": at_risk,
            "underutilized": underutilized,
            "suggestions": suggestions,
        }

    @staticmethod
    def _generate_suggestions(
        overloaded: list[dict[str, Any]],
        underutilized: list[dict[str, Any]],
        tenant_id: str,
        date_from: date,
        date_to: date,
    ) -> list[str]:
        """Generate rebalancing suggestions.

        Args:
            overloaded: List of overloaded user capacity dicts.
            underutilized: List of underutilized user capacity dicts.
            tenant_id: Tenant scope identifier.
            date_from: Start of date range.
            date_to: End of date range.

        Returns:
            List of suggestion strings.
        """
        suggestions: list[str] = []

        if not overloaded:
            suggestions.append("Team capacity is within normal ranges.")
            return suggestions

        if not underutilized:
            suggestions.append(
                "All team members are at or over capacity. Consider hiring or deferring work."
            )
            return suggestions

        for over in overloaded:
            for under in underutilized:
                under_available = float(under["available_hours"]) - float(
                    under["estimated_hours"]
                )
                over_overage = float(over["estimated_hours"]) - float(
                    over["available_hours"]
                )
                transferable = min(under_available, over_overage)
                if transferable > 2:
                    suggestions.append(
                        f"Move ~{transferable:.0f}h of tasks from {over['user_id']} "
                        f"to {under['user_id']} (has {under_available:.0f}h free)"
                    )
                    break

        return suggestions if suggestions else [
            "Review individual workloads for rebalancing opportunities."
        ]

    # -- Overdue detection -------------------------------------------------

    @staticmethod
    def get_overdue_tasks(
        tenant_id: str,
        assignee_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Get overdue tasks.

        Args:
            tenant_id: Tenant scope identifier.
            assignee_id: Optional filter by assignee.
            page: Page number.
            page_size: Items per page.

        Returns:
            Dict with items, total, page, page_size.
        """
        qs = Task.objects.filter(
            tenant_id=tenant_id,
            due_date__lt=date.today(),
        ).exclude(status__in=["done", "cancelled"])

        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = list(qs.order_by("due_date")[start:end])

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def get_upcoming_deadlines(
        tenant_id: str,
        days: int = 7,
        assignee_id: str | None = None,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Get tasks with upcoming deadlines.

        Args:
            tenant_id: Tenant scope identifier.
            days: Number of days ahead to look.
            assignee_id: Optional filter by assignee.
            page_size: Maximum items.

        Returns:
            Dict with items and total.
        """
        deadline = date.today() + timedelta(days=days)
        qs = Task.objects.filter(
            tenant_id=tenant_id,
            due_date__gte=date.today(),
            due_date__lte=deadline,
        ).exclude(status__in=["done", "cancelled"])

        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)

        total = qs.count()
        items = list(qs.order_by("due_date")[:page_size])

        return {
            "items": items,
            "total": total,
        }
