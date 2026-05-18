"""Editorial Calendar service — SP-004 business logic.

Handles calendar entry CRUD, workload calculation, pipeline management,
and color-coded content type handling.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from apps.strategy.models import EditorialCalendar

logger = logging.getLogger(__name__)


class CalendarService:
    """Service for editorial calendar operations."""

    @staticmethod
    def create_entry(
        tenant_id: str,
        title: str,
        content_type: str,
        platform: str = "",
        strategy_id: str | None = None,
        campaign_id: str | None = None,
        assignee_id: str | None = None,
        due_date: date | None = None,
        publish_date: date | None = None,
        priority: int = 3,
        estimated_hours: float | None = None,
        notes: str = "",
    ) -> EditorialCalendar:
        """Create a new editorial calendar entry.

        Args:
            tenant_id: Tenant scope.
            title: Content piece title.
            content_type: Content type slug.
            platform: Target platform.
            strategy_id: Parent strategy UUID.
            campaign_id: Campaign UUID.
            assignee_id: Assignee UUID.
            due_date: Internal deadline.
            publish_date: Publication date.
            priority: 1-5 (1 = highest).
            estimated_hours: Work estimate.
            notes: Planning notes.

        Returns:
            Created EditorialCalendar entry.
        """
        entry = EditorialCalendar.objects.create(
            tenant_id=tenant_id,
            title=title,
            content_type=content_type,
            platform=platform,
            strategy_id=strategy_id if strategy_id else None,
            campaign_id=campaign_id if campaign_id else None,
            assignee_id=assignee_id if assignee_id else None,
            due_date=due_date,
            publish_date=publish_date,
            priority=priority,
            estimated_hours=estimated_hours,
            notes=notes,
        )
        logger.info("Created calendar entry %s for tenant %s", entry.id, tenant_id)
        return entry

    @staticmethod
    def calculate_workload(
        assignee_id: str,
        date_from: date,
        date_to: date,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Calculate workload for a team member over a date range.

        Args:
            assignee_id: Team member UUID.
            date_from: Start date.
            date_to: End date.
            tenant_id: Optional tenant filter.

        Returns:
            Workload dict with daily breakdown, overloaded/underloaded flags.
        """
        qs = EditorialCalendar.objects.filter(
            assignee_id=assignee_id,
            due_date__gte=date_from,
            due_date__lte=date_to,
        )
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        assignments = list(qs)
        workload: dict[str, dict[str, Any]] = {}
        current = date_from
        while current <= date_to:
            day_str = current.isoformat()
            day_items = [a for a in assignments if a.due_date == current]
            est_hours = sum(
                float(a.estimated_hours or 0) for a in day_items
            )
            # Default capacity: 8 hours
            capacity = 8.0
            utilization = est_hours / capacity if capacity > 0 else 0
            workload[day_str] = {
                "items": len(day_items),
                "estimated_hours": round(est_hours, 2),
                "capacity": capacity,
                "utilization": round(utilization, 4),
            }
            current += timedelta(days=1)

        overloaded = [
            {"date": d, **data}
            for d, data in workload.items()
            if data["utilization"] > 1.0
        ]
        underloaded = [
            {"date": d, **data}
            for d, data in workload.items()
            if data["utilization"] < 0.5
        ]
        avg_util = (
            statistics.mean(w["utilization"] for w in workload.values())
            if workload else 0
        )

        return {
            "workload": workload,
            "overloaded": overloaded,
            "underloaded": underloaded,
            "avg_utilization": round(avg_util, 4),
            "total_days": len(workload),
            "overloaded_days": len(overloaded),
            "underloaded_days": len(underloaded),
        }

    @staticmethod
    def get_calendar_view(
        tenant_id: str,
        date_from: date,
        date_to: date,
        status_filter: list[str] | None = None,
        assignee_id: str | None = None,
        content_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get calendar entries for a visual calendar view.

        Args:
            tenant_id: Tenant scope.
            date_from: Start date.
            date_to: End date.
            status_filter: Optional status filter.
            assignee_id: Optional assignee filter.
            content_type: Optional content type filter.

        Returns:
            List of calendar entry dicts with color coding.
        """
        qs = EditorialCalendar.objects.filter(
            tenant_id=tenant_id,
            publish_date__gte=date_from,
            publish_date__lte=date_to,
        )
        if status_filter:
            qs = qs.filter(status__in=status_filter)
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)
        if content_type:
            qs = qs.filter(content_type=content_type)

        entries = []
        for entry in qs.order_by("publish_date", "priority"):
            entries.append({
                "id": str(entry.id),
                "title": entry.title,
                "content_type": entry.content_type,
                "content_type_label": entry.get_content_type_display(),
                "color_code": entry.color_code,
                "platform": entry.platform,
                "status": entry.status,
                "status_label": entry.get_status_display(),
                "publish_date": entry.publish_date.isoformat() if entry.publish_date else None,
                "due_date": entry.due_date.isoformat() if entry.due_date else None,
                "assignee_id": str(entry.assignee_id) if entry.assignee_id else None,
                "priority": entry.priority,
                "estimated_hours": float(entry.estimated_hours) if entry.estimated_hours else None,
                "actual_hours": float(entry.actual_hours) if entry.actual_hours else None,
                "notes": entry.notes,
            })
        return entries

    @staticmethod
    def transition_status(
        entry_id: str,
        tenant_id: str,
        new_status: str,
    ) -> EditorialCalendar:
        """Move an entry to the next pipeline stage.

        Args:
            entry_id: Entry UUID.
            tenant_id: Tenant scope.
            new_status: New status value.

        Returns:
            Updated EditorialCalendar.
        """
        valid = [c[0] for c in EditorialCalendar.Status.choices]
        if new_status not in valid:
            raise ValueError(f"Invalid status: {new_status}. Must be one of: {valid}")

        entry = EditorialCalendar.objects.get(id=entry_id, tenant_id=tenant_id)
        old = entry.status
        entry.status = new_status
        if new_status == EditorialCalendar.Status.PUBLISHED:
            entry.actual_hours = entry.estimated_hours  # Simplified tracking
        entry.save(update_fields=["status", "actual_hours", "updated_at"])
        logger.info("Calendar entry %s: %s → %s", entry_id, old, new_status)
        return entry

    @staticmethod
    def get_pipeline_summary(tenant_id: str) -> dict[str, Any]:
        """Get a summary of entries by pipeline stage.

        Args:
            tenant_id: Tenant scope.

        Returns:
            Dict with counts per stage and upcoming deadlines.
        """
        from django.db.models import Count

        status_counts = EditorialCalendar.objects.filter(
            tenant_id=tenant_id,
        ).values("status").annotate(count=Count("id"))

        pipeline = {status: 0 for status, _ in EditorialCalendar.Status.choices}
        for sc in status_counts:
            pipeline[sc["status"]] = sc["count"]

        # Upcoming deadlines (next 7 days)
        upcoming = EditorialCalendar.objects.filter(
            tenant_id=tenant_id,
            due_date__lte=date.today() + timedelta(days=7),
            due_date__gte=date.today(),
            status__in=[
                EditorialCalendar.Status.IDEATION,
                EditorialCalendar.Status.IN_CREATION,
                EditorialCalendar.Status.REVIEW,
            ],
        ).count()

        return {
            "pipeline": pipeline,
            "total_entries": sum(pipeline.values()),
            "upcoming_deadlines": upcoming,
        }


import statistics  # noqa: E402
