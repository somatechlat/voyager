"""VoyantSearchService — Semantic search via Voyant/Milvus."""

from __future__ import annotations

import logging
from typing import Any

from voyant_bridge.client import voyant_client

logger = logging.getLogger(__name__)


class VoyantSearchService:
    """Service for semantic search via Voyant/Milvus.

    Wraps ``/api/v1/search/query`` and ``/api/v1/search/index``
    with an agent-memory oriented interface.
    """

    DEFAULT_COLLECTION: str = "agent_memory"
    DEFAULT_LIMIT: int = 10

    async def search_agent_memory(
        self,
        query: str,
        agent_id: str,
        tenant_id: str,
        token: str,
        limit: int = 10,
        collection: str = "agent_memory",
    ) -> list[dict[str, Any]]:
        """Search agent memory by semantic similarity.

        Used by: ``ai_agents.services.memory`` (context assembly).

        :param query: Natural language query describing what to recall.
        :param agent_id: Identifier of the agent whose memory to search.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :param limit: Max results (default: 10).
        :param collection: Vector collection name.
        :returns: List of result dicts with ``id``, ``score``, ``metadata``.
        """
        filters = {"agent_id": agent_id, "tenant_id": tenant_id}
        results = await voyant_client.search_similar(
            query=query,
            collection=collection,
            limit=limit,
            token=token,
            filters=filters,
        )
        logger.info(
            "Agent memory search: agent=%s query='%s...' results=%d",
            agent_id,
            query[:40],
            len(results),
        )
        return results

    async def store_memory(
        self,
        content: str,
        metadata: dict[str, Any],
        agent_id: str,
        tenant_id: str,
        token: str,
        item_id: str | None = None,
    ) -> str:
        """Store a memory entry with embedding.

        Used by: ``ai_agents.services.memory`` (experience logging).

        :param content: Text content to embed and store.
        :param metadata: Dict with additional metadata.
        :param agent_id: Identifier of the agent owning the memory.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :param item_id: Optional custom memory ID.
        :returns: The stored item ID.
        """
        memory_metadata: dict[str, Any] = {
            **metadata,
            "agent_id": agent_id,
            "tenant_id": tenant_id,
            "content_preview": content[:200],
        }
        result = await voyant_client.index_document(
            text=content,
            metadata=memory_metadata,
            token=token,
            item_id=item_id,
        )
        stored_id: str = result["id"]
        logger.info(
            "Agent memory stored: agent=%s item=%s dimensions=%s",
            agent_id,
            stored_id,
            result.get("dimensions"),
        )
        return stored_id

    async def forget_memory(
        self,
        item_id: str,
        agent_id: str,
        token: str,
    ) -> dict[str, str]:
        """Delete a stored memory entry.

        :param item_id: ID of the memory to delete.
        :param agent_id: Agent identifier (for audit logging).
        :param token: Bearer JWT token.
        :returns: Dict with ``status`` and ``item_id``.
        """
        result = await voyant_client.delete_indexed_document(item_id, token)
        logger.info("Agent memory deleted: agent=%s item=%s", agent_id, item_id)
        return result

    async def search_similar_documents(
        self,
        query: str,
        tenant_id: str,
        token: str,
        limit: int = 10,
        collection: str = "documents",
    ) -> list[dict[str, Any]]:
        """Search for semantically similar documents.

        Used by: strategy (market research document retrieval).

        :param query: Search query text.
        :param tenant_id: Tenant identifier.
        :param token: Bearer JWT token.
        :param limit: Max results (default: 10).
        :param collection: Document collection name.
        :returns: List of result dicts.
        """
        filters = {"tenant_id": tenant_id}
        return await voyant_client.search_similar(
            query=query,
            collection=collection,
            limit=limit,
            token=token,
            filters=filters,
        )
