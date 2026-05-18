"""Resource limit schemas."""

from __future__ import annotations

from typing import Any

from ninja import Schema


class ResourceLimitSchema(Schema):
    """Agent resource limit record."""

    id: int
    agent_id: int
    tenant_id: str
    max_api_calls: int
    used_api_calls: int
    max_memory_mb: int
    used_memory_mb: int
    max_cost_per_day: float
    used_cost_today: float
    throttle_factor: float
    last_reset_at: str


class ResourceStatusSchema(Schema):
    """Detailed resource status with utilization percentages."""

    agent_id: int
    agent_name: str
    agent_status: str
    resources: dict[str, Any]
    throttle_factor: float
    last_reset_at: str


class ConsumeResourcesRequest(Schema):
    """Request body for consuming resources."""

    api_calls: int = 0
    memory_mb: int = 0
    cost: float = 0.0


class ResourceCheckResponse(Schema):
    """Response for resource limit check."""

    action: str
    resource: str | None
    throttle_factor: float


class ResetResourcesResponse(Schema):
    """Response for resetting daily counters."""

    reset_count: int
