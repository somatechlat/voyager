"""Agent CRUD schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ninja import Schema


class AgentConfigSchema(Schema):
    """Agent configuration sub-document."""

    model: str = "claude-3.5-sonnet"
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str = ""
    tools: list[str] = []
    memory_enabled: bool = True


class AgentResourcesSchema(Schema):
    """Agent resource budget and usage sub-document."""

    max_api_calls: int = 100
    max_memory_mb: int = 512
    max_cost_per_day: float = 5.0
    used_api_calls: int = 0
    used_memory_mb: int = 0
    used_cost_today: float = 0.0


class AgentSchema(Schema):
    """Full agent representation."""

    id: int
    tenant_id: str
    name: str
    agent_type: str
    status: str
    config: dict[str, Any]
    resources: dict[str, Any]
    schedule: str = ""
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AgentCreateSchema(Schema):
    """Request body for creating an agent."""

    tenant_id: str
    name: str
    agent_type: str
    model: str = "claude-3.5-sonnet"
    temperature: float = 0.7
    max_tokens: int = 4096
    memory_enabled: bool = True
    schedule: str = ""
    resources: dict[str, Any] | None = None


class AgentUpdateSchema(Schema):
    """Request body for updating an agent."""

    name: str | None = None
    config: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    schedule: str | None = None
    status: str | None = None


class AgentListResponse(Schema):
    """Paginated response for agent listing."""

    items: list[AgentSchema]
    total: int


class RunAgentRequest(Schema):
    """Request body for running an agent."""

    objective: str
    params: dict[str, Any] = {}
    context: dict[str, Any] = {}


class RunAgentResponse(Schema):
    """Response for agent execution."""

    status: str
    agent_id: str
    agent_type: str
    output: dict[str, Any]
    api_calls: int
    cost: float
    error: str = ""
