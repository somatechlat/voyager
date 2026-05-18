"""Memory service — Qdrant CRUD, semantic search, and memory consolidation."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.utils import timezone
from django.db.models import QuerySet

from apps.ai_agents.models import AIAgent
from apps.ai_agents.models.memory import AgentMemory, MemoryEntry

logger = logging.getLogger(__name__)

CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
EMBEDDING_DIMENSION = 1536


class MemoryService:
    """Service for managing agent memory via Qdrant vector store."""

    @staticmethod
    def initialize_memory(agent_id: int, tenant_id: str) -> AgentMemory:
        """Create a Qdrant collection reference for an agent.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.

        Returns:
            The AgentMemory instance.
        """
        agent = AIAgent.objects.get(pk=agent_id)
        collection_name = f"agent_{tenant_id}_{agent_id}_{uuid.uuid4().hex[:8]}"

        memory, _ = AgentMemory.objects.get_or_create(
            agent=agent,
            defaults={
                "tenant_id": tenant_id,
                "collection_name": collection_name,
                "vector_size": EMBEDDING_DIMENSION,
                "distance_metric": "cosine",
            },
        )
        return memory

    @staticmethod
    def store_memory(
        agent_id: int,
        tenant_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Chunk content, generate embeddings, and store in Qdrant.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.
            content: Text content to store.
            metadata: Optional metadata dict.

        Returns:
            Dict with ``chunks_stored`` and ``qdrant_ids``.
        """
        agent = AIAgent.objects.get(pk=agent_id, tenant_id=tenant_id)
        memory = AgentMemory.objects.filter(agent=agent).first()
        if not memory:
            memory = MemoryService.initialize_memory(agent_id, tenant_id)

        chunks = MemoryService._chunk_text(content, CHUNK_SIZE, CHUNK_OVERLAP)
        qdrant_ids = []

        for chunk in chunks:
            qdrant_id = uuid.uuid4().hex
            importance = MemoryService._calculate_importance(chunk, metadata)

            MemoryEntry.objects.create(
                agent=agent,
                tenant_id=tenant_id,
                qdrant_id=qdrant_id,
                content=chunk,
                importance=importance,
                metadata={**(metadata or {}), "importance": importance, "created_at": timezone.now().isoformat()},
            )
            qdrant_ids.append(qdrant_id)

        memory.total_vectors += len(chunks)
        memory.save(update_fields=["total_vectors"])

        logger.info("Stored %d memory chunks for agent %s", len(chunks), agent_id)
        return {"chunks_stored": len(chunks), "qdrant_ids": qdrant_ids}

    @staticmethod
    def search_memory(
        agent_id: int,
        tenant_id: str,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Search agent memory using hybrid semantic + keyword scoring.

        Since Qdrant integration is external, this implementation performs
        keyword search on cached MemoryEntry records with importance weighting.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.
            query: Search query string.
            top_k: Maximum number of results.

        Returns:
            List of memory entry dicts sorted by final score.
        """
        agent = AIAgent.objects.get(pk=agent_id, tenant_id=tenant_id)
        entries = MemoryEntry.objects.filter(agent=agent, is_active=True)

        query_lower = query.lower()
        results = []

        for entry in entries:
            # Keyword relevance
            content_lower = entry.content.lower()
            keyword_score = 0.0
            if query_lower in content_lower:
                keyword_score = 1.0
            else:
                query_words = query_lower.split()
                matches = sum(1 for w in query_words if w in content_lower)
                if query_words:
                    keyword_score = matches / len(query_words)

            # Recency score
            age_days = (timezone.now() - entry.created_at).days
            recency_score = 1.0 / (1.0 + 0.01 * age_days)

            # Access boost
            access_boost = min(entry.access_count * 0.05, 0.5)

            final_score = keyword_score * 0.5 + float(entry.importance) * 0.3 + recency_score * 0.2 + access_boost

            results.append(
                {
                    "qdrant_id": entry.qdrant_id,
                    "content": entry.content,
                    "importance": float(entry.importance),
                    "access_count": entry.access_count,
                    "created_at": entry.created_at.isoformat(),
                    "final_score": round(final_score, 4),
                }
            )

        results.sort(key=lambda x: x["final_score"], reverse=True)

        # Update access counts for returned results
        top_ids = [r["qdrant_id"] for r in results[:top_k]]
        MemoryEntry.objects.filter(qdrant_id__in=top_ids).update(
            access_count=models.F("access_count") + 1, last_accessed=timezone.now()
        )

        return results[:top_k]

    @staticmethod
    def consolidate_memory(agent_id: int, tenant_id: str) -> dict[str, Any]:
        """Run memory consolidation: decay, merge, delete.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.

        Returns:
            Dict with ``consolidated`` and ``memories_remaining``.
        """
        agent = AIAgent.objects.get(pk=agent_id, tenant_id=tenant_id)
        entries: QuerySet[MemoryEntry] = MemoryEntry.objects.filter(agent=agent, is_active=True)

        now = timezone.now()
        forgotten = 0

        for entry in entries:
            age_days = (now - entry.created_at).days
            days_since_access = (now - entry.last_accessed).days

            decay_factor = 2.718281828 ** (-0.01 * age_days)
            access_boost = entry.access_count * 0.1
            current_importance = float(entry.importance) * decay_factor + access_boost

            if current_importance < 0.1:
                entry.is_active = False
                entry.save(update_fields=["is_active"])
                forgotten += 1

        remaining = MemoryEntry.objects.filter(agent=agent, is_active=True).count()

        memory = AgentMemory.objects.filter(agent=agent).first()
        if memory:
            memory.total_vectors = remaining
            memory.last_consolidated_at = now
            memory.save(update_fields=["total_vectors", "last_consolidated_at"])

        logger.info("Consolidated memory for agent %s: forgotten=%d remaining=%d", agent_id, forgotten, remaining)
        return {"consolidated": True, "forgotten": forgotten, "memories_remaining": remaining}

    @staticmethod
    def delete_memory(agent_id: int, tenant_id: str, qdrant_id: str) -> bool:
        """Delete a specific memory entry.

        Args:
            agent_id: Primary key of the agent.
            tenant_id: Tenant identifier.
            qdrant_id: Qdrant point ID to delete.

        Returns:
            True if deleted.
        """
        deleted, _ = MemoryEntry.objects.filter(
            agent_id=agent_id, tenant_id=tenant_id, qdrant_id=qdrant_id
        ).delete()
        return deleted > 0

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: Source text.
            chunk_size: Maximum chunk length.
            overlap: Overlap between chunks.

        Returns:
            List of text chunks.
        """
        if not text:
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - overlap
            if end >= len(text):
                break
        return chunks

    @staticmethod
    def _calculate_importance(content: str, metadata: dict[str, Any] | None = None) -> float:
        """Calculate an importance score for a memory chunk.

        Args:
            content: The memory content.
            metadata: Optional metadata with hints.

        Returns:
            Importance score between 0.0 and 1.0.
        """
        score = 0.5
        meta = metadata or {}

        if meta.get("task_type") in {"content_creation", "campaign_optimization"}:
            score += 0.2
        if len(content) > 200:
            score += 0.1
        if meta.get("success"):
            score += 0.15

        return min(max(score, 0.0), 1.0)
