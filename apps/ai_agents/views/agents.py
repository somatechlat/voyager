"""Agent CRUD views."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.ai_agents.models import AIAgent
from apps.ai_agents.serializers import (
    AgentCreateSchema,
    AgentListResponse,
    AgentSchema,
    AgentUpdateSchema,
    RunAgentRequest,
    RunAgentResponse,
)
from apps.ai_agents.services.orchestration import AgentOrchestrator


def create_agent(request: HttpRequest, payload: AgentCreateSchema) -> AIAgent:
    """Create and configure a new AI agent."""
    return AgentOrchestrator.create_agent(
        tenant_id=payload.tenant_id,
        name=payload.name,
        agent_type=payload.agent_type,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        memory_enabled=payload.memory_enabled,
        schedule=payload.schedule,
        resources=payload.resources,
    )


def list_agents(
    request: HttpRequest,
    tenant_id: str,
    agent_type: str = "",
) -> AgentListResponse:
    """List agents for a tenant with optional type filter."""
    agents = AgentOrchestrator.list_agents(
        tenant_id=tenant_id,
        agent_type=agent_type or None,
    )
    return AgentListResponse(
        items=_serialize_agents(agents),
        total=len(agents),
    )


def get_agent(request: HttpRequest, agent_id: int) -> AIAgent:
    """Get a single agent by ID."""
    return AIAgent.objects.get(pk=agent_id)


def update_agent(
    request: HttpRequest, agent_id: int, payload: AgentUpdateSchema
) -> AIAgent:
    """Update an agent's configuration."""
    agent = AIAgent.objects.get(pk=agent_id)
    if payload.name is not None:
        agent.name = payload.name
    if payload.config is not None:
        agent.config = {**(agent.config or {}), **payload.config}
    if payload.resources is not None:
        agent.resources = {**(agent.resources or {}), **payload.resources}
    if payload.schedule is not None:
        agent.schedule = payload.schedule
    if payload.status is not None:
        agent.status = payload.status
    agent.save()
    return agent


def delete_agent(request: HttpRequest, agent_id: int) -> dict[str, bool]:
    """Delete an agent and its associated data."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    deleted = AgentOrchestrator.delete_agent(agent_id, tenant_id)
    return {"deleted": deleted}


def run_agent(
    request: HttpRequest, agent_id: int, payload: RunAgentRequest
) -> RunAgentResponse:
    """Execute a task on an agent."""
    result = AgentOrchestrator.run_agent(
        agent_id=agent_id,
        task=payload.dict(),
    )
    if result.get("status") == "error":
        return RunAgentResponse(
            status="error",
            agent_id=str(agent_id),
            agent_type="",
            output={},
            api_calls=0,
            cost=0.0,
            error=result.get("error", ""),
        )
    return RunAgentResponse(
        status=result.get("status", "ok"),
        agent_id=result.get("agent_id", str(agent_id)),
        agent_type=result.get("agent_type", ""),
        output=result.get("output", {}),
        api_calls=result.get("api_calls", 0),
        cost=result.get("cost", 0.0),
    )


def _serialize_agents(agents: list[AIAgent]) -> list[AgentSchema]:
    """Convert agent queryset to schema list."""
    return [
        AgentSchema(
            id=a.id,
            tenant_id=a.tenant_id,
            name=a.name,
            agent_type=a.agent_type,
            status=a.status,
            config=a.config or {},
            resources=a.resources or {},
            schedule=a.schedule,
            last_run_at=a.last_run_at,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in agents
    ]
