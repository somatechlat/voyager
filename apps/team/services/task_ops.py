"""Task operations service — assignment, status, comments, time, bulk, subtasks.

Provides operational methods for task workflow: assignment, status transitions,
comments, time entries, bulk updates, dependency management, and subtasks.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from django.db import transaction

from apps.team.models import Task, TaskComment, TaskTimeEntry
from apps.team.services.task_core import TaskCoreService, TaskServiceError

logger = logging.getLogger(__name__)

SUPPORTED_BULK_FIELDS = [
    "status",
    "assignee_id",
    "priority",
    "due_date",
    "task_type",
    "project_id",
    "client_id",
    "campaign_id",
]

VALID_STATUS_TRANSITIONS = {
    "todo": ["in_progress", "cancelled"],
    "in_progress": ["todo", "done", "cancelled"],
    "done": ["in_progress"],
    "cancelled": ["todo"],
}


class TaskOpsService:
    """Operational service for task workflow management."""

    # -- Assignment --------------------------------------------------------

    @staticmethod
    def assign_task(task_id: int, tenant_id: str, assignee_id: str) -> Task:
        """Assign a task to a user.

        Args:
            task_id: Task primary key.
            tenant_id: Tenant scope identifier.
            assignee_id: User ID to assign to.

        Returns:
            The updated Task instance.
        """
        task = TaskCoreService.get_task(task_id, tenant_id)
        task.assignee_id = assignee_id
        task.save()
        logger.info("Assigned task #%d to %s (tenant %s)", task_id, assignee_id, tenant_id)
        return task

    # -- Status transitions ------------------------------------------------

    @staticmethod
    def transition_status(task_id: int, tenant_id: str, new_status: str) -> Task:
        """Transition a task to a new status.

        Validates the transition and checks dependency blockers
        when transitioning to 'done'.

        Args:
            task_id: Task primary key.
            tenant_id: Tenant scope identifier.
            new_status: Target status.

        Returns:
            The updated Task instance.

        Raises:
            TaskServiceError: If transition is invalid or blocked.
        """
        task = TaskCoreService.get_task(task_id, tenant_id)
        current_status = task.status

        valid_targets = VALID_STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in valid_targets and new_status != current_status:
            raise TaskServiceError(
                f"Invalid transition: {current_status} -> {new_status}. "
                f"Valid targets: {valid_targets}"
            )

        if new_status == "done":
            blockers = task.blocked_by()
            if blockers:
                blocker_str = ", ".join(str(b) for b in blockers)
                raise TaskServiceError(f"Cannot complete task: blocked by {blocker_str}")

        task.status = new_status
        task.save()
        logger.info("Task #%d status: %s -> %s", task_id, current_status, new_status)
        return task

    # -- Comments ----------------------------------------------------------

    @staticmethod
    def add_comment(
        task_id: int,
        tenant_id: str,
        author_id: str,
        content: str,
        attachments: list[str] | None = None,
    ) -> TaskComment:
        """Add a comment to a task.

        Args:
            task_id: Task primary key.
            tenant_id: Tenant scope identifier.
            author_id: Comment author user ID.
            content: Comment text.
            attachments: Optional attachment references.

        Returns:
            The created TaskComment instance.
        """
        task = TaskCoreService.get_task(task_id, tenant_id)
        comment = TaskComment.objects.create(
            task=task,
            author_id=author_id,
            content=content,
            mentions=[],
            attachments=attachments or [],
        )
        logger.info("Added comment #%d to task #%d", comment.id, task_id)
        return comment

    @staticmethod
    def list_comments(
        task_id: int, tenant_id: str, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """List comments on a task.

        Returns:
            Dict with items, total, page, page_size.
        """
        TaskCoreService.get_task(task_id, tenant_id)
        qs = TaskComment.objects.filter(task_id=task_id)
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = list(qs.order_by("created_at")[start:end])
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # -- Time entries ------------------------------------------------------

    @staticmethod
    def log_time(
        task_id: int,
        tenant_id: str,
        user_id: str,
        started_at: datetime,
        ended_at: datetime | None = None,
        duration_seconds: int | None = None,
        description: str = "",
    ) -> TaskTimeEntry:
        """Log time against a task.

        Args:
            task_id: Task primary key.
            tenant_id: Tenant scope identifier.
            user_id: User logging the time.
            started_at: When work began.
            ended_at: When work ended.
            duration_seconds: Explicit duration override.
            description: Work description.

        Returns:
            The created TaskTimeEntry instance.
        """
        task = TaskCoreService.get_task(task_id, tenant_id)
        entry = TaskTimeEntry.objects.create(
            task=task,
            user_id=user_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            description=description,
        )
        logger.info("Logged time entry #%d on task #%d", entry.id, task_id)
        return entry

    @staticmethod
    def list_time_entries(
        task_id: int, tenant_id: str, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """List time entries for a task.

        Returns:
            Dict with items, total, page, page_size.
        """
        TaskCoreService.get_task(task_id, tenant_id)
        qs = TaskTimeEntry.objects.filter(task_id=task_id)
        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = list(qs.order_by("-started_at")[start:end])
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # -- Bulk operations ---------------------------------------------------

    @staticmethod
    @transaction.atomic
    def bulk_update(tenant_id: str, task_ids: list[int], updates: dict[str, Any]) -> dict[str, Any]:
        """Bulk update multiple tasks.

        Args:
            tenant_id: Tenant scope identifier.
            task_ids: List of task IDs to update.
            updates: Field-value pairs to apply.

        Returns:
            Dict with 'updated' count and 'skipped' list.
        """
        skipped: list[dict[str, Any]] = []
        updated_count = 0

        for field in updates:
            if field not in SUPPORTED_BULK_FIELDS:
                raise TaskServiceError(
                    f"Field '{field}' not supported for bulk update. "
                    f"Supported: {SUPPORTED_BULK_FIELDS}"
                )

        for task_id in task_ids:
            try:
                task = Task.objects.get(id=task_id, tenant_id=tenant_id)
            except Task.DoesNotExist:
                skipped.append({"task_id": task_id, "reason": "not found"})
                continue

            if updates.get("status") == "done":
                blockers = task.blocked_by()
                if blockers:
                    skipped.append({"task_id": task_id, "reason": f"blocked by {blockers}"})
                    continue

            for field, value in updates.items():
                if field == "due_date" and isinstance(value, str):
                    value = datetime.strptime(value, "%Y-%m-%d").date()
                setattr(task, field, value)
            task.save()
            updated_count += 1

        return {"updated": updated_count, "skipped": skipped}

    # -- Dependency management ---------------------------------------------

    @staticmethod
    def add_dependency(task_id: int, tenant_id: str, depends_on_task_id: int) -> Task:
        """Add a dependency to a task.

        Args:
            task_id: Task to modify.
            tenant_id: Tenant scope identifier.
            depends_on_task_id: Task that must be completed first.

        Returns:
            The updated Task instance.
        """
        task = TaskCoreService.get_task(task_id, tenant_id)
        deps: list[int] = list(task.dependencies or [])
        if depends_on_task_id not in deps:
            deps.append(depends_on_task_id)
            task.dependencies = deps
            task.save()
        return task

    @staticmethod
    def remove_dependency(task_id: int, tenant_id: str, depends_on_task_id: int) -> Task:
        """Remove a dependency from a task.

        Args:
            task_id: Task to modify.
            tenant_id: Tenant scope identifier.
            depends_on_task_id: Dependency to remove.

        Returns:
            The updated Task instance.
        """
        task = TaskCoreService.get_task(task_id, tenant_id)
        deps: list[int] = list(task.dependencies or [])
        if depends_on_task_id in deps:
            deps.remove(depends_on_task_id)
            task.dependencies = deps
            task.save()
        return task

    # -- Subtask management ------------------------------------------------

    @staticmethod
    def add_subtask(task_id: int, tenant_id: str, title: str) -> Task:
        """Add a subtask to a task.

        Args:
            task_id: Task primary key.
            tenant_id: Tenant scope identifier.
            title: Subtask title.

        Returns:
            The updated Task instance.
        """
        task = TaskCoreService.get_task(task_id, tenant_id)
        subs: list[dict[str, Any]] = list(task.subtasks or [])
        subs.append({"id": str(uuid.uuid4())[:8], "title": title, "done": False})
        task.subtasks = subs
        task.save()
        return task

    @staticmethod
    def toggle_subtask(task_id: int, tenant_id: str, subtask_id: str) -> Task:
        """Toggle a subtask's done status.

        Args:
            task_id: Task primary key.
            tenant_id: Tenant scope identifier.
            subtask_id: Subtask ID to toggle.

        Returns:
            The updated Task instance.
        """
        task = TaskCoreService.get_task(task_id, tenant_id)
        subs: list[dict[str, Any]] = list(task.subtasks or [])
        for sub in subs:
            if sub.get("id") == subtask_id:
                sub["done"] = not sub.get("done", False)
                break
        task.subtasks = subs
        task.save()
        return task
