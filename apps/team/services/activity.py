"""Activity feed service — logging, querying, and aggregating activity events.

Provides a centralized activity feed system for tracking actions across
tasks, messages, and other platform resources.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from django.db.models import Count, Func

from apps.team.models import ActivityFeed

logger = logging.getLogger(__name__)

# Event type display mapping per spec
EVENT_ICONS = {
    "task.created": {"icon": "clipboard", "color": "blue"},
    "task.assigned": {"icon": "user", "color": "purple"},
    "task.completed": {"icon": "check", "color": "green"},
    "task.overdue": {"icon": "clock", "color": "red"},
    "task.updated": {"icon": "pencil", "color": "yellow"},
    "task.commented": {"icon": "comment", "color": "blue"},
    "message.sent": {"icon": "message", "color": "blue"},
    "comment.replied": {"icon": "reply", "color": "purple"},
    "mention.detected": {"icon": "at", "color": "orange"},
    "campaign.launched": {"icon": "target", "color": "green"},
    "user.login": {"icon": "key", "color": "gray"},
    "settings.changed": {"icon": "cog", "color": "gray"},
}


class ActivityServiceError(Exception):
    """Raised when an activity service operation fails."""

    pass


class ActivityService:
    """Service layer for activity feed operations."""

    # -- Logging -----------------------------------------------------------

    @staticmethod
    def log_activity(
        tenant_id: str,
        actor_id: str,
        action_type: str,
        target_type: str = "",
        target_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> ActivityFeed:
        """Create an activity feed entry.

        Args:
            tenant_id: Tenant scope identifier.
            actor_id: UUID of the user who performed the action.
            action_type: Type of action (e.g. 'task.created').
            target_type: Type of resource affected.
            target_id: ID of the affected resource.
            metadata: Additional context as key-value pairs.

        Returns:
            The created ActivityFeed instance.
        """
        entry = ActivityFeed.objects.create(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id or "",
            metadata=metadata or {},
        )
        logger.debug(
            "Logged activity %s by %s: %s on %s:%s",
            action_type,
            actor_id,
            action_type,
            target_type,
            target_id,
        )
        return entry

    @staticmethod
    def log_task_created(
        tenant_id: str, actor_id: str, task_id: int, task_title: str
    ) -> ActivityFeed:
        """Log a task creation event.

        Args:
            tenant_id: Tenant scope identifier.
            actor_id: User who created the task.
            task_id: Created task ID.
            task_title: Task title for display.

        Returns:
            The created ActivityFeed instance.
        """
        return ActivityService.log_activity(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action_type="task.created",
            target_type="task",
            target_id=str(task_id),
            metadata={"task_title": task_title},
        )

    @staticmethod
    def log_task_assigned(
        tenant_id: str,
        actor_id: str,
        task_id: int,
        task_title: str,
        assignee_id: str,
    ) -> ActivityFeed:
        """Log a task assignment event.

        Args:
            tenant_id: Tenant scope identifier.
            actor_id: User who assigned the task.
            task_id: Task ID.
            task_title: Task title for display.
            assignee_id: New assignee user ID.

        Returns:
            The created ActivityFeed instance.
        """
        return ActivityService.log_activity(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action_type="task.assigned",
            target_type="task",
            target_id=str(task_id),
            metadata={"task_title": task_title, "assignee_id": assignee_id},
        )

    @staticmethod
    def log_task_completed(
        tenant_id: str, actor_id: str, task_id: int, task_title: str
    ) -> ActivityFeed:
        """Log a task completion event.

        Args:
            tenant_id: Tenant scope identifier.
            actor_id: User who completed the task.
            task_id: Completed task ID.
            task_title: Task title for display.

        Returns:
            The created ActivityFeed instance.
        """
        return ActivityService.log_activity(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action_type="task.completed",
            target_type="task",
            target_id=str(task_id),
            metadata={"task_title": task_title},
        )

    @staticmethod
    def log_message_sent(
        tenant_id: str, actor_id: str, channel_id: int, message_preview: str
    ) -> ActivityFeed:
        """Log a message sent event.

        Args:
            tenant_id: Tenant scope identifier.
            actor_id: Message sender user ID.
            channel_id: Channel ID.
            message_preview: Preview of message content.

        Returns:
            The created ActivityFeed instance.
        """
        return ActivityService.log_activity(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action_type="message.sent",
            target_type="message_channel",
            target_id=str(channel_id),
            metadata={"preview": message_preview[:100]},
        )

    # -- Querying ----------------------------------------------------------

    @staticmethod
    def get_feed(
        tenant_id: str,
        actor_id: str | None = None,
        action_type: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Query the activity feed with filters.

        Args:
            tenant_id: Tenant scope identifier.
            actor_id: Filter by actor.
            action_type: Filter by action type.
            target_type: Filter by target type.
            target_id: Filter by target ID.
            date_from: Start of date range.
            date_to: End of date range.
            page: Page number.
            page_size: Items per page.

        Returns:
            Dict with items, total, page, page_size.
        """
        qs = ActivityFeed.objects.filter(tenant_id=tenant_id)

        if actor_id:
            qs = qs.filter(actor_id=actor_id)
        if action_type:
            qs = qs.filter(action_type=action_type)
        if target_type:
            qs = qs.filter(target_type=target_type)
        if target_id:
            qs = qs.filter(target_id=target_id)
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = list(qs.order_by("-created_at")[start:end])

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def get_recent_activity(
        tenant_id: str, hours: int = 24, page_size: int = 50
    ) -> dict[str, Any]:
        """Get recent activity from the last N hours.

        Args:
            tenant_id: Tenant scope identifier.
            hours: Number of hours to look back.
            page_size: Maximum items to return.

        Returns:
            Dict with items and total.
        """
        since = datetime.now() - timedelta(hours=hours)
        return ActivityService.get_feed(
            tenant_id=tenant_id, date_from=since, page=1, page_size=page_size
        )

    # -- Aggregation -------------------------------------------------------

    @staticmethod
    def get_stats(
        tenant_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, Any]:
        """Get aggregated activity statistics.

        Args:
            tenant_id: Tenant scope identifier.
            date_from: Start of date range.
            date_to: End of date range.

        Returns:
            Dict with aggregated counts by action_type, actor, and day.
        """
        qs = ActivityFeed.objects.filter(tenant_id=tenant_id)

        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        total = qs.count()

        action_counts = dict(
            qs.values("action_type").annotate(count=Count("id")).values_list(
                "action_type", "count"
            )
        )

        actor_counts = dict(
            qs.values("actor_id").annotate(count=Count("id")).values_list(
                "actor_id", "count"
            )
        )

        daily_counts = dict(
            qs.annotate(day=Func("created_at", function="DATE"))
            .values("day")
            .annotate(count=Count("id"))
            .values_list("day", "count")
        )
        daily_counts = {str(k): v for k, v in daily_counts.items()}

        return {
            "tenant_id": tenant_id,
            "total_events": total,
            "events_by_action_type": action_counts,
            "events_by_actor": actor_counts,
            "events_by_day": daily_counts,
            "date_from": date_from,
            "date_to": date_to,
        }

    @staticmethod
    def enrich_entry(entry: ActivityFeed) -> dict[str, Any]:
        """Enrich an activity entry with icon and display metadata.

        Args:
            entry: ActivityFeed instance to enrich.

        Returns:
            Dict with original fields plus display metadata.
        """
        icon_info = EVENT_ICONS.get(entry.action_type, {"icon": "circle", "color": "gray"})
        return {
            "id": entry.id,
            "tenant_id": entry.tenant_id,
            "actor_id": entry.actor_id,
            "action_type": entry.action_type,
            "target_type": entry.target_type,
            "target_id": entry.target_id,
            "metadata": entry.metadata,
            "created_at": entry.created_at,
            "display": icon_info,
        }

    @staticmethod
    def group_by_day(
        tenant_id: str,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Group activity entries by day.

        Args:
            tenant_id: Tenant scope identifier.
            date_from: Start of date range.
            date_to: End of date range.

        Returns:
            Dict mapping date strings to lists of enriched entries.
        """
        result = ActivityService.get_feed(
            tenant_id=tenant_id,
            date_from=date_from,
            date_to=date_to,
            page=1,
            page_size=500,
        )

        grouped: dict[str, list[dict[str, Any]]] = {}
        for entry in result["items"]:
            day_key = entry.created_at.date().isoformat()
            if day_key not in grouped:
                grouped[day_key] = []
            grouped[day_key].append(ActivityService.enrich_entry(entry))

        return grouped
