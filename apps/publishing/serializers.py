"""Serializers for Publishing module.

Provides Django Ninja compatible input/output schemas for all
publishing endpoints. Schemas use type annotations for automatic
validation.
"""

from __future__ import annotations

from typing import Any

from ninja import Schema

# ---------------------------------------------------------------------------
# Scheduled Post Schemas
# ---------------------------------------------------------------------------


class PlatformPublishConfig(Schema):
    """Platform-specific publish configuration."""

    platform: str
    account_id: str
    publish_type: str = "feed"
    caption: str = ""
    hashtags: list[str] = []
    location_json: dict[str, Any] | None = None
    first_comment: str = ""
    link_override: str = ""
    alt_text: str = ""


class ScheduledPostCreateIn(Schema):
    """Input for creating a scheduled post."""

    content_id: str | None = None
    platforms: list[PlatformPublishConfig]
    scheduled_at: str
    timezone: str = "UTC"
    approval_required: bool = False


class ScheduledPostOut(Schema):
    """Output for a scheduled post."""

    id: str
    tenant_id: str
    content_id: str | None
    campaign_id: str | None
    platform: str
    account_id: str
    publish_type: str
    caption: str
    hashtags: list[str]
    media_urls: list[str]
    link: str
    alt_text: str
    first_comment: str
    scheduled_at: str
    timezone: str
    status: str
    priority: int
    approval_status: str
    platform_post_id: str
    publish_attempts: int
    last_error: str
    published_at: str | None
    created_by: str
    created_at: str
    updated_at: str
    tags: list[str]


# ---------------------------------------------------------------------------
# Calendar Schemas
# ---------------------------------------------------------------------------


class CalendarFilterIn(Schema):
    """Filters for calendar views."""

    platforms: list[str] = []
    status: list[str] = []
    campaigns: list[str] = []
    date_range: dict[str, str] | None = None
    tags: list[str] = []


class CalendarPostOut(Schema):
    """Output for a calendar post entry."""

    id: str
    platform: str
    caption: str
    scheduled_at: str
    status: str
    priority: int
    color: str
    publish_type: str
    media_count: int
    link: str
    account_id: str
    tags: list[str]


class RescheduleResultOut(Schema):
    """Output for drag-and-drop reschedule."""

    adjusted: bool
    new_time: str = ""
    reason: str = ""
    conflicts: list[dict[str, Any]] = []
    requires_user_decision: bool = False
    message: str = ""


# ---------------------------------------------------------------------------
# Queue Schemas
# ---------------------------------------------------------------------------


class QueueEntryOut(Schema):
    """Output for a queue entry."""

    id: str
    post_id: str
    platform: str
    caption: str
    scheduled_at: str
    status: str
    priority: int
    retry_count: int
    next_retry_at: str | None
    overflow_reason: str
    created_at: str


class QueueStatusOut(Schema):
    """Output for queue status."""

    total: int
    pending: int
    processed: int
    overflowed: int


# ---------------------------------------------------------------------------
# Approval Schemas
# ---------------------------------------------------------------------------


class WorkflowStepIn(Schema):
    """Input for a workflow step."""

    step: int
    name: str
    approvers: list[str]
    timeout_hours: int = 24
    escalate_to: str = ""
    actions: list[str] = []
    condition: str = ""


class ApprovalWorkflowCreateIn(Schema):
    """Input for creating an approval workflow."""

    name: str
    type: str
    steps: list[WorkflowStepIn]
    auto_approve_on_timeout: bool = False


class ApprovalActionOut(Schema):
    """Output for an approval action."""

    step: int
    action: str
    approver_id: str
    comment: str
    created_at: str


# ---------------------------------------------------------------------------
# Retry Schemas
# ---------------------------------------------------------------------------


class RetryResultOut(Schema):
    """Output for a retry scheduling operation."""

    retryable: bool
    error_type: str
    attempt: int
    delay_seconds: int = 0
    retry_at: str = ""
    action: str
    notify: str


# ---------------------------------------------------------------------------
# Bulk Import Schemas
# ---------------------------------------------------------------------------


class BulkImportRowErrorOut(Schema):
    """Output for a single row error."""

    row: int
    field: str = ""
    error: str = ""


class BulkImportResultOut(Schema):
    """Output for bulk import operation."""

    valid: bool
    total_rows: int
    valid_rows: int
    error_rows: int
    created: int
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    dry_run: bool


# ---------------------------------------------------------------------------
# Recurring Post Schemas
# ---------------------------------------------------------------------------


class RecurringPostCreateIn(Schema):
    """Input for creating a recurring post."""

    name: str
    platform: str
    account_id: str
    cron_expression: str
    content_pool: list[dict[str, Any]]
    variation_strategy: str = "round_robin"
    base_content: dict[str, Any] = {}
    start_date: str
    end_date: str | None = None
    timezone: str = "UTC"
    tags: list[str] = []


class RecurringPostOut(Schema):
    """Output for a recurring post."""

    id: str
    name: str
    platform: str
    account_id: str
    cron_expression: str
    variation_strategy: str
    is_active: bool
    instance_count: int
    created_by: str
    created_at: str
