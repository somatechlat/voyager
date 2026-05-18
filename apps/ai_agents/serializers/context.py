"""Context assembly schemas."""

from __future__ import annotations

from typing import Any

from ninja import Schema


class AssembleContextRequest(Schema):
    """Request body for context assembly."""

    task_type: str
    brand_data: dict[str, Any] = {}
    audience_data: list[dict[str, Any]] = []
    performance_data: dict[str, Any] = {}
    current_state: dict[str, Any] = {}


class AssembledContextResponse(Schema):
    """Response containing assembled context."""

    agent_id: str
    agent_type: str
    task_type: str
    brand: dict[str, Any]
    audience: list[dict[str, Any]]
    performance: dict[str, Any]
    memories: list[str]
    current_state: dict[str, Any]
    task_specific: dict[str, Any]
    token_estimate: int


class ContextSnapshotSchema(Schema):
    """Persisted context snapshot."""

    task_type: str
    brand_context: dict[str, Any]
    audience_context: list[dict[str, Any]]
    performance_context: dict[str, Any]
    memory_ids: list[str]
    current_state: dict[str, Any]
    token_estimate: int
    assembled_at: str


class ContextListResponse(Schema):
    """Response for context history listing."""

    items: list[ContextSnapshotSchema]
    total: int
