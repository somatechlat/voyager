"""Context assembly views."""

from __future__ import annotations

from django.http import HttpRequest

from apps.ai_agents.serializers import (
    AssembleContextRequest,
    AssembledContextResponse,
    ContextListResponse,
    ContextSnapshotSchema,
)
from apps.ai_agents.services.context import ContextAssembler


def assemble_context(
    request: HttpRequest, agent_id: int, payload: AssembleContextRequest
) -> AssembledContextResponse:
    """Assemble comprehensive context for an agent task."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    context = ContextAssembler.assemble_context(
        agent_id=agent_id,
        tenant_id=tenant_id,
        task_type=payload.task_type,
        brand_data=payload.brand_data or None,
        audience_data=payload.audience_data or None,
        performance_data=payload.performance_data or None,
        current_state=payload.current_state or None,
    )
    return AssembledContextResponse(
        agent_id=context["agent_id"],
        agent_type=context["agent_type"],
        task_type=context["task_type"],
        brand=context["brand"],
        audience=context["audience"],
        performance=context["performance"],
        memories=context["memories"],
        current_state=context["current_state"],
        task_specific=context["task_specific"],
        token_estimate=context["token_estimate"],
    )


def list_contexts(request: HttpRequest, agent_id: int, limit: int = 10) -> ContextListResponse:
    """List recent context snapshots for an agent."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    contexts = ContextAssembler.get_recent_contexts(
        agent_id=agent_id, tenant_id=tenant_id, limit=limit
    )
    return ContextListResponse(
        items=[
            ContextSnapshotSchema(
                task_type=c["task_type"],
                brand_context=c["brand_context"],
                audience_context=c["audience_context"],
                performance_context=c["performance_context"],
                memory_ids=c["memory_ids"],
                current_state=c["current_state"],
                token_estimate=c["token_estimate"],
                assembled_at=c["assembled_at"],
            )
            for c in contexts
        ],
        total=len(contexts),
    )
