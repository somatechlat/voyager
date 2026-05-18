"""Memory management views."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.ai_agents.models import AIAgent
from apps.ai_agents.models.memory import AgentMemory, MemoryEntry
from apps.ai_agents.serializers import (
    ConsolidateMemoryResponse,
    SearchMemoryRequest,
    SearchMemoryResponse,
    SearchMemoryResult,
    StoreMemoryRequest,
    StoreMemoryResponse,
    MemorySchema,
    MemoryEntrySchema,
)
from apps.ai_agents.services.memory import MemoryService


def get_memory_info(request: HttpRequest, agent_id: int) -> AgentMemory:
    """Get the memory collection info for an agent."""
    return AgentMemory.objects.get(agent_id=agent_id)


def get_memory_entries(
    request: HttpRequest, agent_id: int, limit: int = 50
) -> list[MemoryEntry]:
    """List memory entries for an agent."""
    return list(
        MemoryEntry.objects.filter(agent_id=agent_id, is_active=True)
        .order_by("-importance")[:limit]
    )


def store_memory(
    request: HttpRequest, agent_id: int, payload: StoreMemoryRequest
) -> StoreMemoryResponse:
    """Store content into agent memory with chunking."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    result = MemoryService.store_memory(
        agent_id=agent_id,
        tenant_id=tenant_id,
        content=payload.content,
        metadata=payload.metadata,
    )
    return StoreMemoryResponse(
        chunks_stored=result["chunks_stored"],
        qdrant_ids=result["qdrant_ids"],
    )


def search_memory(
    request: HttpRequest, agent_id: int, payload: SearchMemoryRequest
) -> SearchMemoryResponse:
    """Search agent memory with hybrid scoring."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    results = MemoryService.search_memory(
        agent_id=agent_id,
        tenant_id=tenant_id,
        query=payload.query,
        top_k=payload.top_k,
    )
    return SearchMemoryResponse(
        results=[
            SearchMemoryResult(
                qdrant_id=r["qdrant_id"],
                content=r["content"],
                importance=r["importance"],
                access_count=r["access_count"],
                created_at=r["created_at"],
                final_score=r["final_score"],
            )
            for r in results
        ],
        total=len(results),
    )


def delete_memory(
    request: HttpRequest, agent_id: int, qdrant_id: str
) -> dict[str, bool]:
    """Delete a specific memory entry."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    deleted = MemoryService.delete_memory(agent_id, tenant_id, qdrant_id)
    return {"deleted": deleted}


def consolidate_memory(
    request: HttpRequest, agent_id: int
) -> ConsolidateMemoryResponse:
    """Run memory consolidation (decay, merge, delete)."""
    tenant_id = request.headers.get("X-Tenant-ID", "")
    result = MemoryService.consolidate_memory(agent_id, tenant_id)
    return ConsolidateMemoryResponse(
        consolidated=result["consolidated"],
        forgotten=result["forgotten"],
        memories_remaining=result["memories_remaining"],
    )
