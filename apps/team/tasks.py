"""Celery tasks for the Team Collaboration module.

Handles deadline reminders, overdue alerts, workload recalculation,
and activity digest generation. Tasks are routed to the ``team`` queue.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from celery import shared_task

from apps.team.models import MessageChannel, Task
from apps.team.services.activity import ActivityService
from apps.team.services.workload import WorkloadService

logger = logging.getLogger(__name__)

REMINDER_DAYS_AHEAD = 1
OVERDUE_CHECK_HOURS = 24


@shared_task(bind=True, max_retries=3)
def send_deadline_reminders(self, tenant_id: str) -> dict[str, Any]:
    """Send deadline reminders for tasks due soon.

    Identifies tasks with due dates within the next 24 hours and
    creates reminder notifications. Tasks already in 'done' or
    'cancelled' status are skipped.

    Args:
        tenant_id: UUID of the tenant scope.

    Returns:
        Dict with reminder count and notified users.
    """
    logger.info("Checking deadline reminders for tenant %s", tenant_id)

    reminder_date = date.today() + timedelta(days=REMINDER_DAYS_AHEAD)
    tasks = Task.objects.filter(
        tenant_id=tenant_id,
        due_date=reminder_date,
    ).exclude(status__in=["done", "cancelled"])

    notified_users: set[str] = set()
    reminder_count = 0

    for task in tasks:
        if task.assignee_id:
            ActivityService.log_activity(
                tenant_id=tenant_id,
                actor_id="system",
                action_type="task.reminder",
                target_type="task",
                target_id=str(task.id),
                metadata={
                    "task_title": task.title,
                    "assignee_id": task.assignee_id,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "message": (
                        f"Task '{task.title}' is due on "
                        f"{task.due_date}"
                    ),
                },
            )
            notified_users.add(task.assignee_id)
            reminder_count += 1

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "reminders_sent": reminder_count,
        "notified_users": list(notified_users),
    }
    logger.info(
        "Sent %d deadline reminders to %d users for tenant %s",
        reminder_count,
        len(notified_users),
        tenant_id,
    )
    return result


@shared_task(bind=True, max_retries=3)
def check_overdue_tasks(self, tenant_id: str) -> dict[str, Any]:
    """Check for overdue tasks and alert assignees.

    Finds tasks past their due date that are not in 'done' or
    'cancelled' status, and logs an overdue activity event for each.

    Args:
        tenant_id: UUID of the tenant scope.

    Returns:
        Dict with overdue count and alerted users.
    """
    logger.info("Checking overdue tasks for tenant %s", tenant_id)

    overdue_tasks = Task.objects.filter(
        tenant_id=tenant_id,
        due_date__lt=date.today(),
    ).exclude(status__in=["done", "cancelled"])

    alerted_users: set[str] = set()
    overdue_count = 0

    for task in overdue_tasks:
        ActivityService.log_activity(
            tenant_id=tenant_id,
            actor_id="system",
            action_type="task.overdue",
            target_type="task",
            target_id=str(task.id),
            metadata={
                "task_title": task.title,
                "assignee_id": task.assignee_id,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "days_overdue": (
                    (date.today() - task.due_date).days
                    if task.due_date
                    else 0
                ),
                "priority": task.priority,
            },
        )
        if task.assignee_id:
            alerted_users.add(task.assignee_id)
        overdue_count += 1

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "overdue_count": overdue_count,
        "alerted_users": list(alerted_users),
    }
    logger.info(
        "Found %d overdue tasks, alerted %d users for tenant %s",
        overdue_count,
        len(alerted_users),
        tenant_id,
    )
    return result


@shared_task(bind=True, max_retries=3)
def recalculate_workload(self, tenant_id: str) -> dict[str, Any]:
    """Recalculate team workload and detect capacity issues.

    Runs capacity analysis for all team members and logs activity
    events for overloaded users.

    Args:
        tenant_id: UUID of the tenant scope.

    Returns:
        Dict with capacity analysis results.
    """
    logger.info("Recalculating workload for tenant %s", tenant_id)

    capacity_result = WorkloadService.check_capacity(
        tenant_id=tenant_id,
        date_from=date.today(),
        date_to=date.today() + timedelta(days=7),
    )

    overload_events = 0
    for user_cap in capacity_result.get("overloaded", []):
        ActivityService.log_activity(
            tenant_id=tenant_id,
            actor_id="system",
            action_type="workload.overload_detected",
            target_type="user",
            target_id=user_cap["user_id"],
            metadata={
                "utilization_rate": user_cap["utilization_rate"],
                "assigned_tasks": user_cap["assigned_tasks"],
                "estimated_hours": str(user_cap["estimated_hours"]),
                "available_hours": str(user_cap["available_hours"]),
                "suggestion": user_cap["suggestion"],
            },
        )
        overload_events += 1

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "members_analyzed": len(capacity_result.get("user_capacities", [])),
        "overloaded_count": len(capacity_result.get("overloaded", [])),
        "at_risk_count": len(capacity_result.get("at_risk", [])),
        "underutilized_count": len(capacity_result.get("underutilized", [])),
        "overload_events_logged": overload_events,
        "suggestions": capacity_result.get("suggestions", []),
    }
    logger.info(
        "Workload recalculation complete for tenant %s: %d overloaded, %d at risk",
        tenant_id,
        result["overloaded_count"],
        result["at_risk_count"],
    )
    return result


@shared_task(bind=True, max_retries=3)
def send_team_digest(self, tenant_id: str) -> dict[str, Any]:
    """Send daily activity digest to team members.

    Aggregates task completions, assignments, and messages from the
    last 24 hours into a digest for each active team member.

    Args:
        tenant_id: UUID of the tenant scope.

    Returns:
        Dict with recipient count and digest summary.
    """
    logger.info("Sending team digest for tenant %s", tenant_id)

    since = datetime.now() - timedelta(hours=24)

    recent_tasks_created = Task.objects.filter(
        tenant_id=tenant_id, created_at__gte=since
    ).count()

    recent_tasks_completed = Task.objects.filter(
        tenant_id=tenant_id,
        status="done",
        updated_at__gte=since,
    ).count()

    activity_stats = ActivityService.get_stats(
        tenant_id=tenant_id, date_from=since
    )

    assignee_ids = list(
        Task.objects.filter(tenant_id=tenant_id)
        .exclude(assignee_id="")
        .values_list("assignee_id", flat=True)
        .distinct()
    )

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "recipients": len(assignee_ids),
        "summary": {
            "tasks_created": recent_tasks_created,
            "tasks_completed": recent_tasks_completed,
            "total_events": activity_stats["total_events"],
        },
    }
    logger.info(
        "Team digest for tenant %s: %d recipients, %d tasks created, %d completed",
        tenant_id,
        len(assignee_ids),
        recent_tasks_created,
        recent_tasks_completed,
    )
    return result


@shared_task(bind=True, max_retries=3)
def archive_old_messages(self, tenant_id: str, days: int = 365) -> dict[str, Any]:
    """Archive or delete messages older than the retention period.

    Direct messages older than 1 year and group channel messages older
    than 2 years are purged per the retention policy.

    Args:
        tenant_id: UUID of the tenant scope.
        days: Retention period in days (default 365).

    Returns:
        Dict with archived count per channel type.
    """
    logger.info("Archiving old messages for tenant %s (older than %d days)", tenant_id, days)

    cutoff = datetime.now() - timedelta(days=days)
    group_cutoff = datetime.now() - timedelta(days=days * 2)

    from apps.team.models import Message

    direct_channels = MessageChannel.objects.filter(
        tenant_id=tenant_id, channel_type="direct"
    )
    direct_ids = list(direct_channels.values_list("id", flat=True))
    direct_deleted = Message.objects.filter(
        channel_id__in=direct_ids, created_at__lt=cutoff
    ).delete()[0]

    group_channels = MessageChannel.objects.filter(
        tenant_id=tenant_id, channel_type="group"
    )
    group_ids = list(group_channels.values_list("id", flat=True))
    group_deleted = Message.objects.filter(
        channel_id__in=group_ids, created_at__lt=group_cutoff
    ).delete()[0]

    result: dict[str, Any] = {
        "status": "ok",
        "task": self.name,
        "tenant_id": tenant_id,
        "direct_messages_deleted": direct_deleted,
        "group_messages_deleted": group_deleted,
    }
    logger.info(
        "Archived %d direct and %d group messages for tenant %s",
        direct_deleted,
        group_deleted,
        tenant_id,
    )
    return result
