"""Task API endpoints for team collaboration.

Provides CRUD operations, assignment, status transitions, comments,
time entries, subtasks, and bulk operations for tasks.
"""

from __future__ import annotations

from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.rbac.auth import VoyagerKeycloakBearer
from apps.team.models import Task, TaskComment, TaskTimeEntry
from apps.team.serializers import (
    BulkTaskResponseSchema,
    BulkTaskUpdateSchema,
    TaskAssignSchema,
    TaskCommentCreateSchema,
    TaskCommentListResponseSchema,
    TaskCommentSchema,
    TaskCreateSchema,
    TaskFilterSchema,
    TaskListResponseSchema,
    TaskSchema,
    TaskStatusSchema,
    TaskUpdateSchema,
    TimeEntryCreateSchema,
    TimeEntryListResponseSchema,
    TimeEntrySchema,
)
from apps.team.services.tasks import TaskService, TaskServiceError

router = Router(auth=VoyagerKeycloakBearer())


def _task_to_dict(task: Task) -> dict[str, Any]:
    """Serialize a Task model to a dict matching TaskSchema."""
    return {
        "id": task.id,
        "tenant_id": task.tenant_id,
        "title": task.title,
        "description": task.description,
        "project_id": task.project_id,
        "client_id": task.client_id,
        "campaign_id": task.campaign_id,
        "assignee_id": task.assignee_id,
        "reporter_id": task.reporter_id,
        "priority": task.priority,
        "status": task.status,
        "task_type": task.task_type,
        "tags": task.tags or [],
        "due_date": task.due_date,
        "estimated_hours": task.estimated_hours,
        "actual_hours": task.actual_hours,
        "dependencies": task.dependencies or [],
        "subtasks": task.subtasks or [],
        "custom_fields": task.custom_fields or {},
        "attachments": task.attachments or [],
        "position": task.position,
        "is_overdue": task.is_overdue(),
        "completion_percentage": task.completion_percentage(),
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }


def _comment_to_dict(comment: TaskComment) -> dict[str, Any]:
    """Serialize a TaskComment to a dict matching TaskCommentSchema."""
    return {
        "id": comment.id,
        "task_id": comment.task_id,
        "author_id": comment.author_id,
        "content": comment.content,
        "mentions": comment.mentions or [],
        "attachments": comment.attachments or [],
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }


def _time_entry_to_dict(entry: TaskTimeEntry) -> dict[str, Any]:
    """Serialize a TaskTimeEntry to a dict matching TimeEntrySchema."""
    return {
        "id": entry.id,
        "task_id": entry.task_id,
        "user_id": entry.user_id,
        "started_at": entry.started_at,
        "ended_at": entry.ended_at,
        "duration_seconds": entry.duration_seconds,
        "description": entry.description,
        "created_at": entry.created_at,
    }


# -- Task CRUD -----------------------------------------------------------


@router.get("", response=TaskListResponseSchema)
def list_tasks(request, filters: TaskFilterSchema):
    """List tasks with filtering and pagination."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        result = TaskService.list_tasks(
            tenant_id=tenant_id,
            project_id=filters.project_id,
            client_id=filters.client_id,
            campaign_id=filters.campaign_id,
            assignee_id=filters.assignee_id,
            reporter_id=filters.reporter_id,
            priority=filters.priority,
            status=filters.status,
            task_type=filters.task_type,
            tags=filters.tags,
            due_date_from=filters.due_date_from,
            due_date_to=filters.due_date_to,
            search=filters.search,
            page=filters.page,
            page_size=filters.page_size,
        )
    except TaskServiceError as exc:
        raise HttpError(400, str(exc))
    return {
        "items": [_task_to_dict(t) for t in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.post("", response=TaskSchema)
def create_task(request, payload: TaskCreateSchema):
    """Create a new task."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        task = TaskService.create_task(
            tenant_id=tenant_id,
            title=payload.title,
            description=payload.description,
            project_id=payload.project_id,
            client_id=payload.client_id,
            campaign_id=payload.campaign_id,
            assignee_id=payload.assignee_id,
            reporter_id=payload.reporter_id or getattr(user, "user_id", ""),
            priority=payload.priority,
            status=payload.status,
            task_type=payload.task_type,
            tags=payload.tags,
            due_date=payload.due_date,
            estimated_hours=payload.estimated_hours,
            actual_hours=payload.actual_hours,
            dependencies=payload.dependencies,
            subtasks=payload.subtasks,
            custom_fields=payload.custom_fields,
            attachments=payload.attachments,
            position=payload.position,
        )
    except TaskServiceError as exc:
        raise HttpError(400, str(exc))
    return _task_to_dict(task)


@router.get("/{task_id}", response=TaskSchema)
def get_task(request, task_id: int):
    """Get a single task by ID."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        task = TaskService.get_task(task_id, tenant_id)
    except TaskServiceError as exc:
        raise HttpError(404, str(exc))
    return _task_to_dict(task)


@router.put("/{task_id}", response=TaskSchema)
def update_task(request, task_id: int, payload: TaskUpdateSchema):
    """Update a task."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    fields = {k: v for k, v in payload.dict().items() if v is not None}
    try:
        task = TaskService.update_task(task_id, tenant_id, **fields)
    except TaskServiceError as exc:
        raise HttpError(400, str(exc))
    return _task_to_dict(task)


@router.delete("/{task_id}")
def delete_task(request, task_id: int):
    """Delete a task."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        TaskService.delete_task(task_id, tenant_id)
    except TaskServiceError as exc:
        raise HttpError(404, str(exc))
    return {"success": True, "deleted": task_id}


# -- Task operations -----------------------------------------------------


@router.post("/{task_id}/assign", response=TaskSchema)
def assign_task(request, task_id: int, payload: TaskAssignSchema):
    """Assign a task to a user."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        task = TaskService.assign_task(task_id, tenant_id, payload.assignee_id)
    except TaskServiceError as exc:
        raise HttpError(400, str(exc))
    return _task_to_dict(task)


@router.post("/{task_id}/status", response=TaskSchema)
def transition_task_status(request, task_id: int, payload: TaskStatusSchema):
    """Transition a task to a new status."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        task = TaskService.transition_status(task_id, tenant_id, payload.status)
    except TaskServiceError as exc:
        raise HttpError(400, str(exc))
    return _task_to_dict(task)


@router.post("/bulk-update", response=BulkTaskResponseSchema)
def bulk_update_tasks(request, payload: BulkTaskUpdateSchema):
    """Bulk update multiple tasks."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        result = TaskService.bulk_update(tenant_id, payload.task_ids, payload.updates)
    except TaskServiceError as exc:
        raise HttpError(400, str(exc))
    return result


# -- Comments ------------------------------------------------------------


@router.get("/{task_id}/comments", response=TaskCommentListResponseSchema)
def list_comments(request, task_id: int, page: int = 1, page_size: int = 20):
    """List comments on a task."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        result = TaskService.list_comments(task_id, tenant_id, page, page_size)
    except TaskServiceError as exc:
        raise HttpError(404, str(exc))
    return {
        "items": [_comment_to_dict(c) for c in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.post("/{task_id}/comments", response=TaskCommentSchema)
def add_comment(request, task_id: int, payload: TaskCommentCreateSchema):
    """Add a comment to a task."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    author_id = getattr(user, "user_id", "")
    try:
        comment = TaskService.add_comment(
            task_id, tenant_id, author_id, payload.content, payload.attachments
        )
    except TaskServiceError as exc:
        raise HttpError(400, str(exc))
    return _comment_to_dict(comment)


# -- Time entries --------------------------------------------------------


@router.get("/{task_id}/time", response=TimeEntryListResponseSchema)
def list_time_entries(request, task_id: int, page: int = 1, page_size: int = 20):
    """List time entries for a task."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        result = TaskService.list_time_entries(task_id, tenant_id, page, page_size)
    except TaskServiceError as exc:
        raise HttpError(404, str(exc))
    return {
        "items": [_time_entry_to_dict(e) for e in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
    }


@router.post("/{task_id}/time", response=TimeEntrySchema)
def log_time(request, task_id: int, payload: TimeEntryCreateSchema):
    """Log time against a task."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    user_id = getattr(user, "user_id", "")
    try:
        entry = TaskService.log_time(
            task_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            duration_seconds=payload.duration_seconds,
            description=payload.description,
        )
    except TaskServiceError as exc:
        raise HttpError(400, str(exc))
    return _time_entry_to_dict(entry)


# -- Subtasks ------------------------------------------------------------


@router.post("/{task_id}/subtasks", response=TaskSchema)
def add_subtask(request, task_id: int, title: str):
    """Add a subtask to a task."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        task = TaskService.add_subtask(task_id, tenant_id, title)
    except TaskServiceError as exc:
        raise HttpError(400, str(exc))
    return _task_to_dict(task)


@router.post("/{task_id}/subtasks/{subtask_id}/toggle", response=TaskSchema)
def toggle_subtask(request, task_id: int, subtask_id: str):
    """Toggle a subtask's done status."""
    user = request.auth
    tenant_id = getattr(user, "tenant_id", "default")
    try:
        task = TaskService.toggle_subtask(task_id, tenant_id, subtask_id)
    except TaskServiceError as exc:
        raise HttpError(400, str(exc))
    return _task_to_dict(task)
