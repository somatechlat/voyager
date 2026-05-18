"""Pydantic schemas (Django Ninja Serializers) for Team Collaboration.

Defines request/response models for tasks, comments, time entries,
message channels, messages, activity feeds, and workload analytics.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ninja import Schema

# ---------------------------------------------------------------------------
# Task schemas
# ---------------------------------------------------------------------------


class SubtaskSchema(Schema):
    """A subtask item within a task."""

    id: str
    title: str
    done: bool = False


class TaskCreateSchema(Schema):
    """Request body for creating a task."""

    title: str
    description: str = ""
    project_id: str = ""
    client_id: str = ""
    campaign_id: str = ""
    assignee_id: str = ""
    reporter_id: str = ""
    priority: str = "P2"
    status: str = "todo"
    task_type: str = ""
    tags: list[str] = []
    due_date: date | None = None
    estimated_hours: Decimal | None = None
    actual_hours: Decimal | None = None
    dependencies: list[int] = []
    subtasks: list[dict[str, Any]] = []
    custom_fields: dict[str, Any] = {}
    attachments: list[str] = []
    position: int = 0


class TaskUpdateSchema(Schema):
    """Request body for updating a task."""

    title: str | None = None
    description: str | None = None
    project_id: str | None = None
    client_id: str | None = None
    campaign_id: str | None = None
    assignee_id: str | None = None
    reporter_id: str | None = None
    priority: str | None = None
    status: str | None = None
    task_type: str | None = None
    tags: list[str] | None = None
    due_date: date | None = None
    estimated_hours: Decimal | None = None
    actual_hours: Decimal | None = None
    dependencies: list[int] | None = None
    subtasks: list[dict[str, Any]] | None = None
    custom_fields: dict[str, Any] | None = None
    attachments: list[str] | None = None
    position: int | None = None


class TaskSchema(Schema):
    """Full task response schema."""

    id: int
    tenant_id: str
    title: str
    description: str
    project_id: str
    client_id: str
    campaign_id: str
    assignee_id: str
    reporter_id: str
    priority: str
    status: str
    task_type: str
    tags: list[str]
    due_date: date | None
    estimated_hours: Decimal | None
    actual_hours: Decimal | None
    dependencies: list[int]
    subtasks: list[dict[str, Any]]
    custom_fields: dict[str, Any]
    attachments: list[str]
    position: int
    is_overdue: bool
    completion_percentage: int
    created_at: datetime
    updated_at: datetime


class TaskListResponseSchema(Schema):
    """Paginated list of tasks."""

    items: list[TaskSchema]
    total: int
    page: int
    page_size: int


class TaskFilterSchema(Schema):
    """Query parameters for filtering tasks."""

    project_id: str | None = None
    client_id: str | None = None
    campaign_id: str | None = None
    assignee_id: str | None = None
    reporter_id: str | None = None
    priority: str | None = None
    status: str | None = None
    task_type: str | None = None
    tags: str | None = None
    due_date_from: date | None = None
    due_date_to: date | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 20


class TaskAssignSchema(Schema):
    """Request body for assigning a task."""

    assignee_id: str


class TaskStatusSchema(Schema):
    """Request body for updating task status."""

    status: str


class BulkTaskUpdateSchema(Schema):
    """Request body for bulk updating tasks."""

    task_ids: list[int]
    updates: dict[str, Any]


class BulkTaskResponseSchema(Schema):
    """Response for bulk task operations."""

    updated: int
    skipped: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Task comment schemas
# ---------------------------------------------------------------------------


class TaskCommentCreateSchema(Schema):
    """Request body for creating a task comment."""

    content: str
    attachments: list[str] = []


class TaskCommentSchema(Schema):
    """Full task comment response."""

    id: int
    task_id: int
    author_id: str
    content: str
    mentions: list[str]
    attachments: list[str]
    created_at: datetime
    updated_at: datetime


class TaskCommentListResponseSchema(Schema):
    """Paginated list of task comments."""

    items: list[TaskCommentSchema]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Task time entry schemas
# ---------------------------------------------------------------------------


class TimeEntryCreateSchema(Schema):
    """Request body for logging time against a task."""

    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    description: str = ""


class TimeEntrySchema(Schema):
    """Full time entry response."""

    id: int
    task_id: int
    user_id: str
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    description: str
    created_at: datetime


class TimeEntryListResponseSchema(Schema):
    """Paginated list of time entries."""

    items: list[TimeEntrySchema]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Message channel schemas
# ---------------------------------------------------------------------------


class ChannelCreateSchema(Schema):
    """Request body for creating a message channel."""

    name: str
    channel_type: str = "group"
    participant_ids: list[str] = []


class ChannelUpdateSchema(Schema):
    """Request body for updating a channel."""

    name: str | None = None
    participant_ids: list[str] | None = None


class ChannelSchema(Schema):
    """Full channel response."""

    id: int
    tenant_id: str
    name: str
    channel_type: str
    participant_ids: list[str]
    created_at: datetime
    updated_at: datetime


class ChannelListResponseSchema(Schema):
    """Paginated list of channels."""

    items: list[ChannelSchema]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Message schemas
# ---------------------------------------------------------------------------


class MessageCreateSchema(Schema):
    """Request body for sending a message."""

    content: str
    attachments: list[str] = []
    thread_parent_id: int | None = None


class MessageSchema(Schema):
    """Full message response."""

    id: int
    channel_id: int
    author_id: str
    content: str
    mentions: list[str]
    attachments: list[str]
    thread_parent_id: int | None
    reply_count: int
    edited_at: datetime | None
    created_at: datetime


class MessageListResponseSchema(Schema):
    """Paginated list of messages."""

    items: list[MessageSchema]
    total: int
    page: int
    page_size: int


class ThreadReplySchema(Schema):
    """Request body for replying to a message in a thread."""

    content: str
    attachments: list[str] = []


# ---------------------------------------------------------------------------
# Activity feed schemas
# ---------------------------------------------------------------------------


class ActivityCreateSchema(Schema):
    """Request body for creating an activity feed entry."""

    actor_id: str
    action_type: str
    target_type: str = ""
    target_id: str = ""
    metadata: dict[str, Any] = {}


class ActivitySchema(Schema):
    """Full activity feed entry response."""

    id: int
    tenant_id: str
    actor_id: str
    action_type: str
    target_type: str
    target_id: str
    metadata: dict[str, Any]
    created_at: datetime


class ActivityListResponseSchema(Schema):
    """Paginated list of activity feed entries."""

    items: list[ActivitySchema]
    total: int
    page: int
    page_size: int


class ActivityFilterSchema(Schema):
    """Query parameters for filtering activity feeds."""

    actor_id: str | None = None
    action_type: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = 1
    page_size: int = 50


class ActivityStatsSchema(Schema):
    """Aggregated activity statistics."""

    tenant_id: str
    total_events: int
    events_by_action_type: dict[str, int]
    events_by_actor: dict[str, int]
    events_by_day: dict[str, int]
    date_from: datetime | None = None
    date_to: datetime | None = None


# ---------------------------------------------------------------------------
# Workload schemas
# ---------------------------------------------------------------------------


class UserWorkloadSchema(Schema):
    """Workload data for a single user."""

    user_id: str
    total_assigned: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    overdue_count: int
    total_estimated_hours: Decimal
    total_actual_hours: Decimal
    upcoming_due_dates: list[dict[str, Any]]


class WorkloadResponseSchema(Schema):
    """Team workload overview."""

    tenant_id: str
    user_workloads: list[UserWorkloadSchema]
    team_totals: dict[str, Any]


class CapacityCheckSchema(Schema):
    """Request body for capacity planning check."""

    user_ids: list[str] = []
    date_from: date | None = None
    date_to: date | None = None


class UserCapacitySchema(Schema):
    """Capacity information for a single user."""

    user_id: str
    assigned_tasks: int
    estimated_hours: Decimal
    available_hours: Decimal
    utilization_rate: float
    status: str
    suggestion: str = ""


class CapacityResponseSchema(Schema):
    """Team capacity planning response."""

    tenant_id: str
    date_from: date | None
    date_to: date | None
    user_capacities: list[UserCapacitySchema]
    overloaded: list[UserCapacitySchema]
    at_risk: list[UserCapacitySchema]
    underutilized: list[UserCapacitySchema]
    suggestions: list[str]
