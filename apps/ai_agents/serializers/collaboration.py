"""Multi-agent collaboration schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Schema


class CollaborationSchema(Schema):
    """Full collaboration representation."""

    id: int
    tenant_id: str
    initiator_agent_id: int
    task_id: str
    pattern: str
    status: str
    delegation_chain: list[str]
    max_depth: int
    messages: list[dict[str, Any]]
    started_at: str | None
    completed_at: str | None
    result_summary: dict[str, Any]
    created_at: datetime


class CreateCollaborationRequest(Schema):
    """Request body for creating a collaboration."""

    tenant_id: str
    initiator_agent_id: int
    task_id: str
    pattern: str
    max_depth: int = 5


class DelegateTaskRequest(Schema):
    """Request body for delegating a task."""

    from_agent_id: int
    to_agent_id: int
    task: dict[str, Any]


class DelegateTaskResponse(Schema):
    """Response for task delegation."""

    status: str
    result: dict[str, Any] | None = None
    chain: list[str] | None = None
    error: str = ""


class CompleteCollaborationRequest(Schema):
    """Request body for completing a collaboration."""

    result_summary: dict[str, Any] = {}


class ActiveCollaborationsResponse(Schema):
    """Response listing active collaborations."""

    items: list[dict[str, Any]]
    total: int
