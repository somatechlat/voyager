"""Task core service — CRUD and listing operations.

Provides create, read, update, delete, and list operations for tasks.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from apps.team.models import Task

logger = logging.getLogger(__name__)


class TaskServiceError(Exception):
    """Raised when a task service operation fails."""


class TaskCoreService:
    """Core CRUD service for task management."""

    @staticmethod
    def create_task(
        tenant_id: str,
        title: str,
        description: str = "",
        project_id: str = "",
        client_id: str = "",
        campaign_id: str = "",
        assignee_id: str = "",
        reporter_id: str = "",
        priority: str = "P2",
        status: str = "todo",
        task_type: str = "",
        tags: list[str] | None = None,
        due_date: date | None = None,
        estimated_hours: Decimal | None = None,
        actual_hours: Decimal | None = None,
        dependencies: list[int] | None = None,
        subtasks: list[dict[str, Any]] | None = None,
        custom_fields: dict[str, Any] | None = None,
        attachments: list[str] | None = None,
        position: int = 0,
    ) -> Task:
        """Create a new task.

        Args:
            tenant_id: Tenant scope identifier.
            title: Task title (required).
            description: Detailed description.
            project_id: Optional project UUID.
            client_id: Optional client UUID.
            campaign_id: Optional campaign UUID.
            assignee_id: Optional assignee user UUID.
            reporter_id: Optional reporter user UUID.
            priority: Priority level (P0-P3).
            status: Initial status.
            task_type: Type of work.
            tags: List of string tags.
            due_date: Deadline date.
            estimated_hours: Estimated effort.
            actual_hours: Logged effort.
            dependencies: List of dependent task IDs.
            subtasks: List of subtask dicts.
            custom_fields: Key-value custom fields.
            attachments: List of attachment refs.
            position: Kanban board position.

        Returns:
            The created Task instance.

        Raises:
            TaskServiceError: If title is empty or fields invalid.
        """
        if not title or not title.strip():
            raise TaskServiceError("Task title is required")

        valid_priorities = [p[0] for p in Task.Priority.choices]
        if priority not in valid_priorities:
            raise TaskServiceError(f"Invalid priority '{priority}'. Valid: {valid_priorities}")

        valid_statuses = [s[0] for s in Task.Status.choices]
        if status not in valid_statuses:
            raise TaskServiceError(f"Invalid status '{status}'. Valid: {valid_statuses}")

        if due_date and isinstance(due_date, str):
            due_date = datetime.strptime(due_date, "%Y-%m-%d").date()

        task = Task.objects.create(
            tenant_id=tenant_id,
            title=title.strip(),
            description=description,
            project_id=project_id or "",
            client_id=client_id or "",
            campaign_id=campaign_id or "",
            assignee_id=assignee_id or "",
            reporter_id=reporter_id or "",
            priority=priority,
            status=status,
            task_type=task_type or "",
            tags=tags or [],
            due_date=due_date,
            estimated_hours=estimated_hours,
            actual_hours=actual_hours,
            dependencies=dependencies or [],
            subtasks=subtasks or [],
            custom_fields=custom_fields or {},
            attachments=attachments or [],
            position=position,
        )
        logger.info("Created task #%d '%s' for tenant %s", task.id, task.title, tenant_id)
        return task

    @staticmethod
    def get_task(task_id: int, tenant_id: str) -> Task:
        """Fetch a single task by ID and tenant.

        Args:
            task_id: Task primary key.
            tenant_id: Tenant scope identifier.

        Returns:
            The Task instance.

        Raises:
            TaskServiceError: If the task does not exist.
        """
        try:
            return Task.objects.get(id=task_id, tenant_id=tenant_id)
        except Task.DoesNotExist:
            raise TaskServiceError(f"Task {task_id} not found")

    @staticmethod
    def list_tasks(
        tenant_id: str,
        project_id: str | None = None,
        client_id: str | None = None,
        campaign_id: str | None = None,
        assignee_id: str | None = None,
        reporter_id: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        tags: str | None = None,
        due_date_from: date | None = None,
        due_date_to: date | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List tasks with filtering and pagination.

        Returns:
            Dict with items, total, page, page_size.
        """
        qs = Task.objects.filter(tenant_id=tenant_id)

        if project_id:
            qs = qs.filter(project_id=project_id)
        if client_id:
            qs = qs.filter(client_id=client_id)
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)
        if reporter_id:
            qs = qs.filter(reporter_id=reporter_id)
        if priority:
            qs = qs.filter(priority=priority)
        if status:
            qs = qs.filter(status=status)
        if task_type:
            qs = qs.filter(task_type=task_type)
        if tags:
            qs = qs.filter(tags__contains=[tags])
        if due_date_from:
            qs = qs.filter(due_date__gte=due_date_from)
        if due_date_to:
            qs = qs.filter(due_date__lte=due_date_to)
        if search:
            qs = qs.filter(title__icontains=search) | qs.filter(description__icontains=search)

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
    def update_task(task_id: int, tenant_id: str, **fields: Any) -> Task:
        """Update a task's fields.

        Args:
            task_id: Task primary key.
            tenant_id: Tenant scope identifier.
            **fields: Field names and values to update.

        Returns:
            The updated Task instance.

        Raises:
            TaskServiceError: If task not found or invalid field.
        """
        task = TaskCoreService.get_task(task_id, tenant_id)

        allowed_fields = {
            "title",
            "description",
            "project_id",
            "client_id",
            "campaign_id",
            "assignee_id",
            "reporter_id",
            "priority",
            "status",
            "task_type",
            "tags",
            "due_date",
            "estimated_hours",
            "actual_hours",
            "dependencies",
            "subtasks",
            "custom_fields",
            "attachments",
            "position",
        }

        for key, value in fields.items():
            if key not in allowed_fields:
                raise TaskServiceError(f"Cannot update field '{key}'")
            if value is not None:
                setattr(task, key, value)

        task.save()
        logger.info("Updated task #%d for tenant %s", task_id, tenant_id)
        return task

    @staticmethod
    def delete_task(task_id: int, tenant_id: str) -> None:
        """Delete a task and its related comments/time entries.

        Args:
            task_id: Task primary key.
            tenant_id: Tenant scope identifier.

        Raises:
            TaskServiceError: If task not found.
        """
        task = TaskCoreService.get_task(task_id, tenant_id)
        task.delete()
        logger.info("Deleted task #%d for tenant %s", task_id, tenant_id)
