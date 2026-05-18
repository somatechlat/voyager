"""Multi-agent collaboration views."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.ai_agents.models.collaboration import AgentCollaboration
from apps.ai_agents.serializers import (
    ActiveCollaborationsResponse,
    CompleteCollaborationRequest,
    CreateCollaborationRequest,
    DelegateTaskRequest,
    DelegateTaskResponse,
)
from apps.ai_agents.services.collaboration import CollaborationService


def create_collaboration(
    request: HttpRequest, payload: CreateCollaborationRequest
) -> AgentCollaboration:
    """Create a new collaboration session."""
    return CollaborationService.create_collaboration(
        tenant_id=payload.tenant_id,
        initiator_agent_id=payload.initiator_agent_id,
        task_id=payload.task_id,
        pattern=payload.pattern,
        max_depth=payload.max_depth,
    )


def list_active_collaborations(
    request: HttpRequest, tenant_id: str
) -> ActiveCollaborationsResponse:
    """List active collaborations for a tenant."""
    collaborations = CollaborationService.list_active_collaborations(tenant_id)
    return ActiveCollaborationsResponse(
        items=collaborations,
        total=len(collaborations),
    )


def delegate_task(
    request: HttpRequest,
    collaboration_id: int,
    payload: DelegateTaskRequest,
) -> DelegateTaskResponse:
    """Delegate a task with circular delegation prevention."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    result = CollaborationService.delegate_task(
        tenant_id=tenant_id,
        collaboration_id=collaboration_id,
        from_agent_id=payload.from_agent_id,
        to_agent_id=payload.to_agent_id,
        task=payload.task,
    )
    return DelegateTaskResponse(
        status=result.get("status", "error"),
        result=result.get("result"),
        chain=result.get("chain"),
        error=result.get("error", ""),
    )


def complete_collaboration(
    request: HttpRequest,
    collaboration_id: int,
    payload: CompleteCollaborationRequest,
) -> dict[str, Any]:
    """Mark a collaboration as completed."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    return CollaborationService.complete_collaboration(
        tenant_id=tenant_id,
        collaboration_id=collaboration_id,
        result_summary=payload.result_summary,
    )


def get_collaboration_messages(
    request: HttpRequest, collaboration_id: int
) -> list[dict[str, Any]]:
    """Get the message log for a collaboration."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    return CollaborationService.get_collaboration_messages(
        tenant_id=tenant_id, collaboration_id=collaboration_id
    )
