"""Resource monitoring views — throttling, status, and reset."""

from __future__ import annotations

from django.http import HttpRequest

from apps.ai_agents.models.agent import AgentResourceLimit
from apps.ai_agents.serializers import (
    ConsumeResourcesRequest,
    ResetResourcesResponse,
    ResourceCheckResponse,
    ResourceStatusSchema,
)
from apps.ai_agents.services.resources import ResourceManager


def get_resource_status(request: HttpRequest, agent_id: int) -> ResourceStatusSchema:
    """Get current resource status for an agent."""
    status = ResourceManager.get_resource_status(agent_id)
    if status.get("status") == "error":
        return ResourceStatusSchema(
            agent_id=agent_id,
            agent_name="",
            agent_status="unknown",
            resources={},
            throttle_factor=1.0,
            last_reset_at="",
        )
    return ResourceStatusSchema(
        agent_id=status["agent_id"],
        agent_name=status["agent_name"],
        agent_status=status["agent_status"],
        resources=status["resources"],
        throttle_factor=status["throttle_factor"],
        last_reset_at=status["last_reset_at"],
    )


def get_resource_limits(request: HttpRequest, agent_id: int) -> AgentResourceLimit:
    """Get raw resource limit record for an agent."""
    return AgentResourceLimit.objects.get(agent_id=agent_id)


def check_resources(request: HttpRequest, agent_id: int) -> ResourceCheckResponse:
    """Check resource limits and get throttle status."""
    result = ResourceManager.check_resources(agent_id)
    return ResourceCheckResponse(
        action=result["action"],
        resource=result.get("resource"),
        throttle_factor=float(result["throttle_factor"]),
    )


def consume_resources(
    request: HttpRequest,
    agent_id: int,
    payload: ConsumeResourcesRequest,
) -> ResourceStatusSchema:
    """Consume resources for an agent."""
    ResourceManager.consume_resources(
        agent_id=agent_id,
        api_calls=payload.api_calls,
        memory_mb=payload.memory_mb,
        cost=payload.cost,
    )
    return get_resource_status(request, agent_id)


def reset_daily_counters(
    request: HttpRequest,
    tenant_id: str = "",
) -> ResetResourcesResponse:
    """Reset daily resource counters."""
    result = ResourceManager.reset_daily_counters(
        tenant_id=tenant_id or None,
    )
    return ResetResourcesResponse(reset_count=result["reset_count"])
